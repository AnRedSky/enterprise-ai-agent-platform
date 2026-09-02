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
        request: 当前 pytest 测试上下文。保留该参数用于维持 fixture 的标准测试上下文接口。

    Returns:
        无；每个异步测试结束后释放当前测试可能创建的数据库连接。

    设计边界：pytest-asyncio 可以为不同异步测试创建不同事件循环，而 AsyncEngine 的连接池
    会缓存绑定旧事件循环的 asyncpg Connection。只按 `integration` / `real_api` 标记释放连接
    不足以覆盖未标记但实际访问数据库的测试，连接可能跨测试保留并在后续同步测试结束时以
    `ResourceWarning: unclosed socket` 形式暴露。统一在每个异步测试结束时 dispose，避免测试
    标记遗漏导致连接池跨事件循环泄漏。生产进程仍使用同一事件循环，不受该测试隔离措施影响。
    """
    del request
    try:
        yield
    finally:
        await engine.dispose()
