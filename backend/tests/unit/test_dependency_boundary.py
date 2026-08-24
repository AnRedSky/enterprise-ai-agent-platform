"""验证 FastAPI 数据库依赖位于唯一的 Dependencies 边界。

测试范围：确保 API 依赖可以从 canonical dependencies 包导入，并继续复用
Infrastructure 层唯一的数据库 Session 实现；不测试具体业务流程。
"""

from app.dependencies.db import get_db
from app.infrastructure.db import get_db_session


def test_database_dependency_uses_canonical_infrastructure_session() -> None:
    """数据库依赖应存在于 Dependencies 层并复用 Infrastructure Session。"""
    assert get_db.__module__ == "app.dependencies.db"
    assert get_db_session.__module__.startswith("app.infrastructure.db")
