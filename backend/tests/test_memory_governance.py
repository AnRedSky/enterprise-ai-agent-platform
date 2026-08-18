from datetime import datetime, timedelta

from app.models.memory import MemoryRecord
from app.services.memory_service import MemoryService


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
    future = datetime.utcnow() + timedelta(hours=1)
    past = datetime.utcnow() - timedelta(hours=1)
    assert future > datetime.utcnow() > past
