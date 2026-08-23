from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


# The tenant-safe bootstrap is executed as a standalone script by PowerShell.
# Python therefore puts this script's directory (not backend/) on sys.path.
# Add the backend application root explicitly before importing app.* for the
# fixture-only database recovery path.
_BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))


_BOOTSTRAP_PATH = Path(__file__).with_name("00_bootstrap_real_api.py")
_SPEC = importlib.util.spec_from_file_location("real_api_bootstrap", _BOOTSTRAP_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load {_BOOTSTRAP_PATH}")
_BOOTSTRAP = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_BOOTSTRAP)

_BOOTSTRAP_ORGANIZATION_ID: str | None = None


def _run_fixture_db(operation):
    """Run one fixture-only DB operation on a fresh async engine/loop."""
    from app.core.config import settings

    async def _run():
        engine = create_async_engine(settings.database_url, pool_pre_ping=True)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with session_factory() as db:
                return await operation(db)
        finally:
            await engine.dispose()

    return asyncio.run(_run())


def _existing_tenant_organization(tenant_id: str):
    """Read the tenant's singleton Organization for fixture recovery."""
    from app.models.organization import Organization
    from uuid import UUID

    async def _load(db):
        result = await db.execute(
            select(Organization).where(Organization.tenant_id == UUID(tenant_id))
        )
        return result.scalar_one_or_none()

    return _run_fixture_db(_load)


def _ensure_existing_organization_owner(organization_id: str, user_id: str) -> str:
    """Make the fresh fixture user the sole active owner of a reused Organization.

    This is test-fixture recovery only. It restores a deterministic owner boundary
    when the local tenant already contains an Organization from an earlier real
    API run, while the actual ownership mutations remain exercised through HTTP.
    """
    from app.models.organization import OrganizationMembership
    from uuid import UUID

    organization_uuid = UUID(organization_id)
    user_uuid = UUID(user_id)

    async def _ensure(db):
        result = await db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization_uuid
            )
        )
        memberships = list(result.scalars().all())
        target = next((item for item in memberships if item.user_id == user_uuid), None)
        if target is None:
            target = OrganizationMembership(
                id=uuid.uuid4(),
                organization_id=organization_uuid,
                user_id=user_uuid,
                status="active",
                role="owner",
            )
            db.add(target)
        for membership in memberships:
            if membership.id != target.id and membership.role == "owner":
                membership.role = "admin"
                if membership.status != "active":
                    membership.status = "active"
        target.status = "active"
        target.role = "owner"
        await db.commit()
        await db.refresh(target)
        return str(target.id)

    return _run_fixture_db(_ensure)


def _ensure_existing_organization_membership(organization_id: str, user_id: str) -> str:
    """Create an active admin membership for the fresh fixture user."""
    from app.models.organization import OrganizationMembership
    from uuid import UUID

    async def _ensure(db):
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

    return _run_fixture_db(_ensure)


def create_organization_fixture(client, owner_username: str, owner_password: str) -> dict[str, str]:
    """Create or reuse the owner's tenant-scoped Organization fixture."""
    global _BOOTSTRAP_ORGANIZATION_ID

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

    if str(organization["tenant_id"]) != owner_tenant_id:
        raise RuntimeError(
            "Organization tenant boundary mismatch: "
            f"organization={organization['tenant_id']} owner={owner_tenant_id}"
        )

    _BOOTSTRAP_ORGANIZATION_ID = str(organization["id"])
    # Whether the Organization was newly created or recovered, establish a
    # deterministic fixture owner before exercising ownership through HTTP.
    _ensure_existing_organization_owner(_BOOTSTRAP_ORGANIZATION_ID, owner_user_id)

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


def create_governed_mock_agent(
    client,
    *,
    model_id: str = "mock-http-404",
    name_prefix: str = "API Retry Agent",
) -> str:
    """Create a deterministic mock agent through the governed Provider/Profile path."""
    if not _BOOTSTRAP_ORGANIZATION_ID:
        raise RuntimeError("Governed mock agent requires an initialized Organization fixture")

    suffix = uuid.uuid4().hex[:8]
    provider = _BOOTSTRAP.request(
        client,
        "POST",
        "/model-providers",
        json={
            "organization_id": _BOOTSTRAP_ORGANIZATION_ID,
            "name": f"API Real Mock Provider {suffix}",
            "provider_type": "mock",
            "provider_name": f"api-real-mock-{suffix}",
            "enabled": True,
        },
    ).json()
    profile = _BOOTSTRAP.request(
        client,
        "POST",
        f"/model-providers/{provider['id']}/profiles",
        json={
            "name": f"api-real-{model_id}-{suffix}",
            "model_type": "chat",
            "model_name": model_id,
            "is_default": True,
        },
    ).json()
    agent = _BOOTSTRAP.request(
        client,
        "POST",
        "/agents",
        json={
            "name": f"{name_prefix} {suffix}",
            "description": "Automated real API governed model fixture agent",
            "system_prompt": "You are a deterministic validation agent.",
            "model_id": model_id,
            "model_profile_id": profile["id"],
        },
    ).json()
    versions = _BOOTSTRAP.request(client, "GET", f"/agents/{agent['id']}/versions").json()
    if not versions:
        raise RuntimeError(f"Agent {agent['id']} was created without a version")
    _BOOTSTRAP.request(
        client,
        "POST",
        f"/agents/{agent['id']}/publish",
        json={"version_id": versions[0]["id"]},
    )
    return agent["id"]


_BOOTSTRAP.create_retry_agent = create_governed_mock_agent
_BOOTSTRAP.create_organization_fixture = create_organization_fixture


if __name__ == "__main__":
    _BOOTSTRAP.main()
