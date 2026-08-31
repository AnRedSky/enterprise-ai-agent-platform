"""Browser E2E 本地数据库隔离与 owner fixture 初始化工具。

职责：在 Browser E2E 每个独立场景开始前清理 Organization 根聚合及其级联数据，
并重新建立一个仅供本地 Browser E2E 使用的 active owner，使 Organization / Provider
等 owner-only 浏览器契约不依赖历史数据库用户或人工录入账号。
边界：仅供本地 Browser E2E 使用，不作为生产数据维护工具，也不执行 Alembic migration。
关键依赖：项目 Settings、SQLAlchemy AsyncSession、Organization/User ORM。
"""

from pathlib import Path
import os
import sys

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.core.security import hash_password
from app.models.core import DEFAULT_TENANT_ID, Tenant, User
from app.models.organization import Organization, OrganizationMembership


E2E_OWNER_USERNAME = os.getenv("BROWSER_E2E_OWNER_USERNAME", "browser_e2e_owner")
E2E_OWNER_PASSWORD = os.getenv("BROWSER_E2E_OWNER_PASSWORD", "BrowserE2EOwner!2026")
E2E_ORGANIZATION_NAME = "Browser E2E Organization"


async def reset_browser_e2e_database() -> None:
    """清理 Organization 聚合并建立 deterministic owner fixture。"""
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(text("TRUNCATE TABLE organizations CASCADE"))

        async with AsyncSession(engine) as session:
            tenant = (await session.execute(
                select(Tenant).where(Tenant.id == DEFAULT_TENANT_ID)
            )).scalar_one_or_none()
            if tenant is None:
                tenant = Tenant(id=DEFAULT_TENANT_ID, name="Default Tenant", status="active")
                session.add(tenant)
                await session.flush()
            elif tenant.status != "active":
                tenant.status = "active"

            owner = (await session.execute(
                select(User).where(User.username == E2E_OWNER_USERNAME)
            )).scalar_one_or_none()
            if owner is None:
                owner = User(
                    username=E2E_OWNER_USERNAME,
                    password_hash=hash_password(E2E_OWNER_PASSWORD),
                    tenant_id=DEFAULT_TENANT_ID,
                    status="active",
                )
                session.add(owner)
                await session.flush()
            else:
                owner.password_hash = hash_password(E2E_OWNER_PASSWORD)
                owner.tenant_id = DEFAULT_TENANT_ID
                owner.status = "active"

            organization = Organization(
                name=E2E_ORGANIZATION_NAME,
                tenant_id=DEFAULT_TENANT_ID,
                status="active",
            )
            session.add(organization)
            await session.flush()
            session.add(
                OrganizationMembership(
                    organization_id=organization.id,
                    user_id=owner.id,
                    status="active",
                    role="owner",
                )
            )
            await session.commit()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    import asyncio

    asyncio.run(reset_browser_e2e_database())
    print(f"BROWSER_E2E_DATABASE_RESET_OK owner={E2E_OWNER_USERNAME}")
