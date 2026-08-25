"""SQLAlchemy 元数据完整性测试。

职责：防止已经退出当前领域模型的历史表被新的 ORM ForeignKey 再次引用。
边界：只检查当前审计模型的历史兼容映射，不替代真实 PostgreSQL migration 或 API 测试。
关键依赖：AuditLog 与 SQLAlchemy 元数据。
"""

from app.models.core import AuditLog


def test_audit_log_legacy_execution_id_is_not_an_orm_foreign_key() -> None:
    """确保已退役的 executions 表不会在当前 ORM 映射中成为审计日志的 ForeignKey 目标。"""
    legacy_foreign_keys = [
        foreign_key
        for foreign_key in AuditLog.__table__.foreign_keys
        if foreign_key.parent.name == "execution_id"
    ]

    assert legacy_foreign_keys == []
