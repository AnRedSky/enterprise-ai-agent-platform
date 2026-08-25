"""Browser E2E 本地数据库隔离工具。

职责：在 Browser E2E 每个独立场景开始前清理 Organization 根聚合及其级联数据，
使项目当前“一 Tenant 一 Organization”的治理约束不会让前一个场景污染后一个场景。
边界：仅供本地 Browser E2E 使用，不作为生产数据维护工具，也不执行 Alembic migration。
关键依赖：项目 Settings 与 SQLAlchemy AsyncEngine；数据库连接来自当前本地环境配置。
"""

from pathlib import Path
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


# 直接以脚本路径启动时，Python 默认只把 scripts/test/e2e 目录加入 sys.path；
# 显式加入 backend 根目录，确保独立 Gate 与 pytest 的 pythonpath 行为一致。
BACKEND_ROOT = Path(__file__).resolve().parents[4]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings


async def reset_browser_e2e_database() -> None:
    """清理 Browser E2E 使用的 Organization 聚合及其数据库级联数据。

    Args:
        无。

    Returns:
        无；完成后当前本地测试数据库不再保留 Organization 根聚合。

    Raises:
        SQLAlchemyError: 数据库不可连接或清理语句执行失败时向 Gate 传播异常。
    """
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.begin() as connection:
            await connection.execute(text("TRUNCATE TABLE organizations CASCADE"))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    import asyncio

    asyncio.run(reset_browser_e2e_database())
    print("BROWSER_E2E_DATABASE_RESET_OK")
