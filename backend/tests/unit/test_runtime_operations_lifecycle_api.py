from uuid import UUID

from app.api.v1.runtime.operations import router


def test_runtime_operations_exposes_provider_and_alert_lifecycle_routes() -> None:
    """验证 Runtime Operations 聚合 router 暴露完整生命周期路由。"""
    routes = {(route.path, tuple(sorted(route.methods or set()))) for route in router.routes}
    assert ("/operations/providers/{provider_id}", ("PATCH",)) in routes
    assert ("/operations/alert-rules/{rule_id}", ("PATCH",)) in routes
    assert ("/operations/alert-rules/evaluate", ("POST",)) in routes


def test_uuid_contract_remains_explicit() -> None:
    """验证 UUID 契约仍保持显式 UUID 类型语义。"""
    assert UUID("00000000-0000-0000-0000-000000000000").version is None
