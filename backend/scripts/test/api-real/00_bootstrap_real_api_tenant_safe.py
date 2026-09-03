from __future__ import annotations

import asyncio
import importlib.util
import os
from pathlib import Path
import sys
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


# Tenant-safe bootstrap 作为独立脚本由 PowerShell 调用，因此显式加入 backend 根目录。
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
    """在独立事件循环和专用 Engine 中执行仅用于测试夹具恢复的数据库操作。"""
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
    """读取指定 Tenant 已存在的唯一 Organization，用于旧 Real API 夹具恢复。"""
    from app.models.organization import Organization
    from uuid import UUID

    async def _load(db):
        result = await db.execute(
            select(Organization).where(Organization.tenant_id == UUID(tenant_id))
        )
        return result.scalar_one_or_none()

    return _run_fixture_db(_load)


def _ensure_existing_organization_owner(organization_id: str, user_id: str) -> str:
    """确保本轮 owner 用户是唯一 active owner，供复用旧 Organization 的夹具使用。"""
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
    """恢复指定用户的 active admin membership，仅用于兼容旧测试夹具。"""
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
    """创建或恢复 owner Tenant 的 Organization，并生成自动加入后的 admin 测试成员。"""
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
    # 旧 Organization 复用时，通过数据库夹具恢复 owner；实际成员权限仍通过 HTTP 更新。
    _ensure_existing_organization_owner(_BOOTSTRAP_ORGANIZATION_ID, owner_user_id)

    member_username = f"api_real_org_member_{uuid.uuid4().hex[:12]}"
    member_password = f"ApiRealTest!{uuid.uuid4().hex[:16]}"
    member = _BOOTSTRAP.request(
        client,
        "POST",
        "/auth/register",
        json={"username": member_username, "password": member_password},
    ).json()

    # /auth/register 已按当前默认 Tenant 的 Organization 语义自动创建 member membership。
    # 这里不能再次 POST /members，否则会稳定命中“用户已经属于该 Organization”的业务冲突。
    members = _BOOTSTRAP.request(
        client,
        "GET",
        f"/organizations/{organization['id']}/members",
    ).json()
    membership = next(
        (item for item in members.get("items", []) if str(item.get("user_id")) == str(member["user_id"])),
        None,
    )
    if membership is None:
        raise RuntimeError(
            "Registered fixture user is not present in the default Organization membership list: "
            f"user_id={member['user_id']} organization_id={organization['id']}"
        )

    # 新注册用户默认是 member；通过正式 HTTP 管理接口提升为 admin，保持权限变更仍经过 API。
    membership = _BOOTSTRAP.request(
        client,
        "PATCH",
        f"/organizations/{organization['id']}/members/{membership['id']}",
        json={"role": "admin"},
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
    """通过受治理 Provider/Profile 路径创建确定性的 mock Agent。"""
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
    # Tenant-safe Gate 必须自行生成隔离 owner，不能继承人工提供的 API_TEST_USERNAME/PASSWORD。
    # /auth/register 当前只允许进入默认 Tenant，因此生成 owner 后才能保证后续成员与 Organization 同属该 Tenant。
    os.environ.pop("API_TEST_USERNAME", None)
    os.environ.pop("API_TEST_PASSWORD", None)
    _BOOTSTRAP.main()
