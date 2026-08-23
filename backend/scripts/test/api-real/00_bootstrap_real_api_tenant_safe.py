from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import uuid

import httpx
from sqlalchemy import select


_BOOTSTRAP_PATH = Path(__file__).with_name("00_bootstrap_real_api.py")
_SPEC = importlib.util.spec_from_file_location("real_api_bootstrap", _BOOTSTRAP_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load {_BOOTSTRAP_PATH}")
_BOOTSTRAP = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_BOOTSTRAP)


def _existing_tenant_organization(tenant_id: str):
    """Read the tenant's singleton Organization for fixture recovery.

    The public Organization list is intentionally membership-scoped. After the
    API correctly rejects a second Organization with HTTP 409, a freshly-created
    bootstrap user therefore cannot discover that existing Organization through
    HTTP until it has a membership. The test fixture may use the database only to
    repair this bootstrap boundary; all subsequent governance operations remain
    real HTTP API calls.
    """
    from app.dependencies.db import SessionLocal
    from app.models.organization import Organization
    from uuid import UUID

    async def _load():
        async with SessionLocal() as db:
            result = await db.execute(
                select(Organization).where(Organization.tenant_id == UUID(tenant_id))
            )
            return result.scalar_one_or_none()

    return asyncio.run(_load())


def _ensure_existing_organization_membership(organization_id: str, user_id: str) -> str:
    """Create an active admin membership for the fresh fixture user.

    This is fixture recovery, not an application authorization shortcut. The
    production API deliberately does not expose tenant-wide Organization lookup
    to users who are not members, so the test harness must establish the initial
    membership before it can continue through the real HTTP surface.
    """
    from app.dependencies.db import SessionLocal
    from app.models.organization import OrganizationMembership
    from uuid import UUID

    async def _ensure():
        async with SessionLocal() as db:
            result = await db.execute(
                select(OrganizationMembership).where(
                    OrganizationMembership.organization_id == UUID(organization_id),
                    OrganizationMembership.user_id == UUID(user_id),
                )
            )
            membership = result.scalar_one_or_none()
            if membership is None:
                membership = OrganizationMembership(
                    id=uuid.uuid4(),
                    organization_id=UUID(organization_id),
                    user_id=UUID(user_id),
                    status="active",
                    role="admin",
                )
                db.add(membership)
            else:
                membership.status = "active"
                if membership.role == "member":
                    membership.role = "admin"
            await db.commit()
            await db.refresh(membership)
            return str(membership.id)

    return asyncio.run(_ensure())


def create_organization_fixture(client, owner_username: str, owner_password: str) -> dict[str, str]:
    """Create or reuse the owner's tenant-scoped Organization fixture.

    Runtime governance resolves Organization scope from the Workflow execution
    tenant, while the authenticated owner carries its tenant in the JWT. The
    Organization endpoint permits only one Organization per Tenant, so a
    rerunnable Real API gate must reuse the existing Organization instead of
    treating HTTP 409 as a bootstrap failure.
    """
    with httpx.Client(base_url=_BOOTSTRAP.BASE_URL, timeout=_BOOTSTRAP.TIMEOUT) as owner_client:
        owner_login = _BOOTSTRAP.request(
            owner_client,
            "POST",
            "/auth/login",
            json={"username": owner_username, "password": owner_password},
        ).json()
        owner_token = owner_login.get("access_token")
        owner_tenant_id = str(owner_login["tenant_id"])
        owner_user_id = str(owner_login["user_id"])
        if not owner_token:
            raise RuntimeError("Owner login response does not contain access_token")
        owner_client.headers["Authorization"] = f"Bearer {owner_token}"
        organizations = _BOOTSTRAP.request(owner_client, "GET", "/organizations").json()

    items = organizations.get("items", [])
    matching = [item for item in items if str(item.get("tenant_id")) == owner_tenant_id]
    organization = matching[0] if matching else None

    if organization is None:
        try:
            organization = _BOOTSTRAP.request(
                client,
                "POST",
                "/organizations",
                json={"name": f"API Real Organization {uuid.uuid4().hex[:8]}"},
            ).json()
        except RuntimeError as exc:
            if "POST /organizations -> 409" not in str(exc):
                raise

            # HTTP GET /organizations is membership-scoped. A new bootstrap user
            # cannot see the existing tenant singleton after the expected 409, so
            # recover the owner membership at the fixture DB boundary and then
            # return to the real HTTP API for the rest of the gate.
            organization_row = _existing_tenant_organization(owner_tenant_id)
            if organization_row is None:
                raise RuntimeError(
                    "Organization creation returned 409, but no Organization exists "
                    f"for owner tenant {owner_tenant_id}"
                ) from exc
            organization = {
                "id": str(organization_row.id),
                "tenant_id": str(organization_row.tenant_id),
                "name": organization_row.name,
                "status": organization_row.status,
            }
            _ensure_existing_organization_membership(str(organization_row.id), owner_user_id)

    if str(organization["tenant_id"]) != owner_tenant_id:
        raise RuntimeError(
            "Organization tenant boundary mismatch: "
            f"organization={organization['tenant_id']} owner={owner_tenant_id}"
        )

    member_username = f"api_real_org_member_{uuid.uuid4().hex[:12]}"
    member_password = f"ApiRealTest!{uuid.uuid4().hex[:16]}"
    member = _BOOTSTRAP.request(
        client,
        "POST",
        "/auth/register",
        json={"username": member_username, "password": member_password},
    ).json()
    membership = _BOOTSTRAP.request(
        client,
        "POST",
        f"/organizations/{organization['id']}/members",
        json={"user_id": member["user_id"], "role": "admin"},
    ).json()

    with httpx.Client(base_url=_BOOTSTRAP.BASE_URL, timeout=_BOOTSTRAP.TIMEOUT) as member_client:
        member_token = _BOOTSTRAP.login_token(member_client, member_username, member_password)

    return {
        "organization_id": str(organization["id"]),
        "membership_id": str(membership["id"]),
        "member_user_id": str(member["user_id"]),
        "member_access_token": member_token,
    }


_BOOTSTRAP.create_organization_fixture = create_organization_fixture

if __name__ == "__main__":
    _BOOTSTRAP.main()
