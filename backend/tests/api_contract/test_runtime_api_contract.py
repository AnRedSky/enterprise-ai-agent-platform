from datetime import datetime, UTC
from uuid import uuid4
from app.schemas.runtime import AuditLogListResponse, ExecutionItem, ExecutionListResponse, ExecutionTimelineResponse


def execution():
    return ExecutionItem(execution_id=uuid4(), request_id="req", trace_id="trace", agent_id=uuid4(), status="success", started_at=datetime.now(UTC))


def test_execution_response_contract():
    response = ExecutionListResponse(items=[execution()], page=1, page_size=20, total=1)
    assert response.page == 1 and response.total == 1


def test_timeline_contract():
    response = ExecutionTimelineResponse(execution=execution(), items=[])
    assert response.execution.status == "success"
    assert response.items == []


def test_audit_contract_is_minimal():
    response = AuditLogListResponse(items=[], page=1, page_size=100, total=0)
    assert response.page_size == 100
