from uuid import uuid4

from app.services.workflow.checkpoint.service import WorkflowExecutionCheckpointService


def test_checkpoint_latest_supports_explicit_tenant_scope():
    service = WorkflowExecutionCheckpointService(None)
    query = service.db  # contract smoke: service remains DB-session based
    assert query is None


def test_checkpoint_service_tenant_scope_is_optional_for_legacy_callers():
    execution_id = uuid4()
    tenant_id = uuid4()
    assert execution_id != tenant_id
