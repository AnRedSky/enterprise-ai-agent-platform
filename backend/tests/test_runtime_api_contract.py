from uuid import uuid4
from datetime import datetime
from app.schemas.runtime import ExecutionItem, ExecutionListResponse, ExecutionTimelineResponse, AuditLogListResponse


def test_execution_response_contract():
    item = ExecutionItem(execution_id=uuid4(), request_id="req", trace_id="trace", agent_id=uuid4(), status="success", started_at=datetime.utcnow())
    response = ExecutionListResponse(items=[item], page=1, page_size=20, total=1)
    assert response.page_size == 20
    assert response.items[0].request_id == "req"


def test_timeline_contract():
    execution = ExecutionItem(execution_id=uuid4(), request_id="req", trace_id="trace", agent_id=uuid4(), status="running", started_at=datetime.utcnow())
    response = ExecutionTimelineResponse(execution=execution, items=[])
    assert response.items == []


def test_audit_contract_is_minimal():
    response = AuditLogListResponse(items=[], page=1, page_size=20, total=0)
    assert response.total == 0
