"""Runtime Audit / Trace 关联 API Contract 测试。

验证四条只读深链路由存在、仅允许 GET，并暴露稳定分页与筛选参数。
"""

from app.api.v1.runtime.correlations import router


def test_runtime_correlation_exposes_all_bidirectional_deep_links() -> None:
    paths = {route.path for route in router.routes}

    assert "/correlations/executions/{execution_id}" in paths
    assert "/correlations/traces/{trace_id}" in paths
    assert "/correlations/audits/{audit_id}" in paths
    assert "/correlations/operator-actions/{operator_action_id}" in paths


def test_runtime_correlation_routes_are_get_only() -> None:
    methods_by_path = {route.path: route.methods for route in router.routes}

    assert methods_by_path["/correlations/executions/{execution_id}"] == {"GET"}
    assert methods_by_path["/correlations/traces/{trace_id}"] == {"GET"}
    assert methods_by_path["/correlations/audits/{audit_id}"] == {"GET"}
    assert methods_by_path["/correlations/operator-actions/{operator_action_id}"] == {"GET"}


def test_runtime_correlation_routes_expose_filter_query_parameters() -> None:
    for route in router.routes:
        names = {parameter.name for parameter in route.dependant.query_params}
        assert {"trace_page", "trace_page_size", "audit_page", "audit_page_size", "trace_event_type", "trace_status", "audit_action", "audit_status"} <= names
