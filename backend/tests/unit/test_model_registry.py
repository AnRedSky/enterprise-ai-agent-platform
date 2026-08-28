"""数据库会话初始化时必须加载的 ORM metadata 注册测试。"""

from app.infrastructure.db.session import SessionLocal
from app.models.core import Base


def test_database_session_registers_model_profile_metadata():
    """直接导入 SessionLocal 也必须注册 model_profiles，避免运行时 FK 解析失败。"""
    assert SessionLocal is not None
    assert "model_profiles" in Base.metadata.tables
    assert "model_providers" in Base.metadata.tables


def test_database_session_registers_delegation_metadata():
    """Delegation 及其依赖表必须同时存在于共享 metadata。"""
    assert "agent_delegations" in Base.metadata.tables
    assert "workflow_executions" in Base.metadata.tables
    assert "agent_versions" in Base.metadata.tables
