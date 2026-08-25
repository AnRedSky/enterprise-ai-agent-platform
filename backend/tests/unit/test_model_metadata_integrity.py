"""SQLAlchemy 元数据完整性测试。

职责：防止已经退出当前领域模型的历史表被新的 ORM ForeignKey 再次引用。
边界：只检查模型元数据映射，不替代真实 PostgreSQL migration 或 API 测试。
关键依赖：app.models 注册的 SQLAlchemy Base 元数据。
"""

from app.models.core import Base


def test_all_model_foreign_keys_resolve_to_registered_tables() -> None:
    """确保 ORM ForeignKey 只引用当前注册的数据库表，避免 flush 阶段出现元数据解析失败。"""
    tables = Base.metadata.tables
    unresolved: list[str] = []
    for table in tables.values():
        for foreign_key in table.foreign_keys:
            target_table = foreign_key.target_fullname.split(".", 1)[0]
            if target_table not in tables:
                unresolved.append(f"{table.name}.{foreign_key.parent.name} -> {foreign_key.target_fullname}")

    assert unresolved == [], f"发现未注册的 ORM ForeignKey: {unresolved}"
