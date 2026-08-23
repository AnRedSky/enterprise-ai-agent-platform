from __future__ import annotations

import importlib.util
from pathlib import Path

import httpx


_BOOTSTRAP_PATH = Path(__file__).with_name("00_bootstrap_real_api.py")
_SPEC = importlib.util.spec_from_file_location("real_api_bootstrap", _BOOTSTRAP_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load {_BOOTSTRAP_PATH}")
_BOOTSTRAP = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_BOOTSTRAP)


def create_organization_fixture(client, owner_username: str, owner_password: str) -> dict[str, str]:
    """Create a tenant and member without changing the bootstrap owner's session.

    Organization creation itself creates an active owner membership. The original
    helper logged in the secondary admin member through the same httpx client,
    replacing its Authorization header. Runtime fixtures created afterwards could
    therefore run under the wrong session and fail the tenant governance boundary.
    Keep the owner token on the fixture client and persist the member token only
    for tests that explicitly need the member boundary.
    """
    organization = _BOOTSTRAP.request(
        client,
        "POST",
        "/organizations",
        json={"name": f"API Real Organization {__import__('uuid').uuid4().hex[:8]}"},
    ).json()
    member_username = f"api_real_org_member_{__import__('uuid').uuid4().hex[:12]}"
    member_password = f"ApiRealTest!{__import__('uuid').uuid4().hex[:16]}"
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
