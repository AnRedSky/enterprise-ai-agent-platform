from __future__ import annotations

import sys
from pathlib import Path

import pytest_asyncio

from app.infrastructure.db import engine

# 确保从 backend 或仓库根目录启动 pytest 时都能解析 app 包，无需额外设置 PYTHONPATH。
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest_asyncio.fixture(autouse=True, loop_scope="function")
async def _dispose_database_engine_between_async_tests(request):
    """隔离 pytest 异步事件循环与 SQLAlchemy 连接池的生命周期。

    Args:
        request: 当前 pytest 测试上下文，用于判断测试是否属于需要外部数据库连接的场景。

    Returns:
        无；数据库集成测试结束后释放本测试事件循环创建的数据库连接。

    设计边界：pytest-asyncio 可以为不同异步测试创建不同事件循环，而 AsyncEngine 的连接池
    会缓存绑定旧事件循环的 asyncpg Connection。若不在数据库集成测试之间释放连接池，后续测试
    可能复用已经关闭事件循环上的连接，表现为 `Event loop is closed`、`proactor.send` 或
    `Connection._cancel was never awaited` 警告。显式使用 function loop scope，使 dispose 与
    创建数据库连接的测试事件循环处于同一生命周期。生产进程仍使用同一事件循环，不受该测试隔离措施影响。
    """
    try:
        yield
    finally:
        if (
            request.node.get_closest_marker("integration") is not None
            or request.node.get_closest_marker("real_api") is not None
        ):
            await engine.dispose()
