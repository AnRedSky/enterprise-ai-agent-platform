from __future__ import annotations

import importlib.util
from pathlib import Path
import uuid

import httpx


_BOOTSTRAP_PATH = Path(__file__).with_name("00_bootstrap_real_api.py")
_SPEC = importlib.util.spec_from_file_location("real_api_bootstrap", _BOOTSTRAP_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load {_BOOTSTRAP_PATH}")
_BOOTSTRAP = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_BOOTSTRAP)


def create_organization_fixture(client, owner_username: str, owner_password: str) -> dict[str, str]:
    """Create or reuse the owner's tenant-scoped Organization fixture.

    Runtime governance resolves Organization scope from the Workflow execution
    tenant, while the authenticated owner carries its tenant in the JWT. The
    Organization endpoint permits only one Organization per Tenant, so a
    rerunnable Real API gate must reuse the existing Organization instead of
    treating HTTP 409 as a bootstrap failure.
    """
    # Login through a separate client so the owner's Authorization header on the
    # fixture client is never replaced while we inspect the tenant boundary.
    with httpx.Client(base_url=_BOOTSTRAP.BASE_URL, timeout=_BOOTSTRAP.TIMEOUT) as owner_client:
        owner_login = _BOOTSTRAP.request(
            owner_client,
            "POST",
            "/auth/login",
            json={"username": owner_username, "password": owner_password},
        ).json()
        owner_token = owner_login.get("access_token")
        owner_tenant_id = str(owner_login["tenant_id"])
        if not owner_token:
            raise RuntimeError("Owner login response does not contain access_token")
        owner_client.headers["Authorization"] = f"Bearer {owner_token}"
        organizations = _BOOTSTRAP.request(owner_client, "GET", "/organizations").json()

    items = organizations.get("items", [])
    matching = [item for item in items if str(item.get("tenant_id")) == owner_tenant_id]
    if matching:
        organization = matching[0]
    else:
        try:
            organization = _BOOTSTRAP.request(
                client,
                "POST",
                "/organizations",
                json={"name": f"API Real Organization {uuid.uuid4().hex[:8]}"},
            ).json()
        except RuntimeError as exc:
            # A concurrent/previous bootstrap may have created the tenant's
            # single Organization after the GET. Re-read rather than creating a
            # second tenant or failing on the expected uniqueness boundary.
            if "POST /organizations -> 409" not in str(exc):
                raise
            organizations = _BOOTSTRAP.request(client, "GET", "/organizations").json()
            items = organizations.get("items", [])
            matching = [item for item in items if str(item.get("tenant_id")) == owner_tenant_id]
            if not matching:
                raise RuntimeError(
                    "Organization creation returned 409, but no Organization was "
                    f"visible for owner tenant {owner_tenant_id}"
                ) from exc
            organization = matching[0]

    # Verify the production API established the same tenant boundary used by
    # the owner's JWT before creating any runtime fixtures.
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

    # Login through a separate client so the owner Authorization header cannot be
    # replaced. The member token remains available to governance boundary tests.
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
