from datetime import datetime
from uuid import uuid4

from app.models.execution import ExecutionEvent
from app.schemas.runtime import ExecutionEventItem


def test_execution_event_metadata_round_trips_through_schema():
    execution_id = uuid4()
    event = ExecutionEvent(
        id=uuid4(),
        execution_id=execution_id,
        trace_id="trace-g02",
        span_type="retrieval",
        status="completed",
        started_at=datetime(2026, 8, 19, 12, 0, 0),
        metadata={
            "knowledge_base_ids": [str(uuid4())],
            "top_k": 3,
            "result_count": 2,
            "citations": ["DOC-1#1", "DOC-2#0"],
            "retrieval_sources": ["lexical", "vector"],
        },
    )

    item = ExecutionEventItem.model_validate(event)

    assert item.trace_id == "trace-g02"
    assert item.span_type == "retrieval"
    assert item.metadata is not None
    assert item.metadata["top_k"] == 3
    assert item.metadata["result_count"] == 2
    assert item.metadata["retrieval_sources"] == ["lexical", "vector"]
