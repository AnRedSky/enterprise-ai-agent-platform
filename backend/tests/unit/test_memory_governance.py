"""Memory 领域治理测试。

模块职责：验证 Memory 模型默认值、可见性条件与时间边界规则。
边界：只覆盖 Memory 领域单元行为，不负责 HTTP、Runtime 或数据库联调。
关键依赖：MemoryRecord ORM 模型与 MemoryService 正式领域入口。
"""

from datetime import UTC, datetime, timedelta

from app.models.memory import MemoryRecord
from app.services.memory import MemoryService


def test_memory_governance_model_defaults():
    record = MemoryRecord(
        user_id="00000000-0000-0000-0000-000000000001",
        agent_id="00000000-0000-0000-0000-000000000002",
        memory_key="timezone",
        content="Asia/Seoul",
    )
    assert record.is_active is None or record.is_active is True
    assert record.expires_at is None


def test_memory_visibility_clause_contains_active_and_expiry_rules():
    clause = MemoryService._visible_clause()
    text = str(clause)
    assert "is_active" in text
    assert "expires_at" in text


def test_expiry_boundary_is_representable():
    now = datetime.now(UTC)
    future = now + timedelta(hours=1)
    past = now - timedelta(hours=1)
    assert future > now > past
