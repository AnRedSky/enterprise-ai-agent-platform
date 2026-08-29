from uuid import UUID

from app.api.v1.runtime.operations import router


def test_runtime_operations_exposes_provider_and_alert_lifecycle_routes() -> None:
    routes = {(route.path, tuple(sorted(route.methods or set()))) for route in router.routes}
    assert ("/api/v1/runtime/operations/providers/{provider_id}", ("PATCH",)) in routes
    assert ("/api/v1/runtime/operations/alert-rules/{rule_id}", ("PATCH",)) in routes
    assert ("/api/v1/runtime/operations/alert-rules/evaluate", ("POST",)) in routes


def test_uuid_contract_remains_explicit() -> None:
    assert UUID("00000000-0000-0000-0000-000000000000").version is None
