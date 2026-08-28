"""Checkpoint tenant write boundary 的单元测试。"""

from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.services.workflow.checkpoint.service import WorkflowExecutionCheckpointService


class _Result:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value


@pytest.mark.asyncio
async def test_append_next_in_transaction_scopes_execution_lookup_to_tenant() -> None:
    tenant_id = uuid4()
    execution_id = uuid4()
    execution = type("Execution", (), {
        "id": execution_id,
        "tenant_id": tenant_id,
        "status": "running",
        "worker_owner": None,
        "worker_attempt": 0,
        "worker_lease_expires_at": None,
    })()
    db = AsyncMock()
    db.execute.side_effect = [_Result(execution), _Result(None)]
    db.flush = AsyncMock()
    service = WorkflowExecutionCheckpointService(db)

    checkpoint = await service.append_next_in_transaction(
        execution_id=execution_id,
        tenant_id=tenant_id,
        execution_status="running",
        state_data={"value": 1},
        checkpoint_reason="test",
    )

    assert checkpoint.sequence == 0
    first_query = db.execute.await_args_list[0].args[0]
    assert tenant_id in first_query.compile().params.values()


@pytest.mark.asyncio
async def test_append_next_in_transaction_rejects_missing_tenant_execution() -> None:
    db = AsyncMock()
    db.execute.return_value = _Result(None)
    service = WorkflowExecutionCheckpointService(db)

    with pytest.raises(HTTPException, match="tenant"):
        await service.append_next_in_transaction(
            execution_id=uuid4(),
            tenant_id=uuid4(),
            execution_status="running",
            state_data={},
            checkpoint_reason="test",
        )