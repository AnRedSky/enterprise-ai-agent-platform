"""Runtime Audit / Trace 关联 API Contract 测试。

职责：验证关联查询的响应 schema、分页集合类型、路径参数边界和 tenant 查询边界。
边界：只验证 API Contract，不启动真实服务，不访问真实数据库。
"""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_runtime_correlation_routes_are_get_only():
    paths = {
        (route.path, tuple(sorted(route.methods or [])))
        for route in app.routes
        if route.path.startswith("/api/v1/runtime/correlations/")
    }
    assert paths == {
        ("/api/v1/runtime/correlations/executions/{execution_id}", ("GET",)),
        ("/api/v1/runtime/correlations/traces/{trace_id}", ("GET",)),
        ("/api/v1/runtime/correlations/audits/{audit_id}", ("GET",)),
        ("/api/v1/runtime/correlations/operator-actions/{operator_action_id}", ("GET",)),
    }


def test_runtime_correlation_requires_bearer_authentication():
    execution_id = "00000000-0000-0000-0000-000000000001"
    response = client.get(f"/api/v1/runtime/correlations/executions/{execution_id}")
    assert response.status_code == 401


def test_runtime_correlation_exposes_concrete_trace_and_audit_item_schemas():
    schemas = app.openapi()["components"]["schemas"]
    correlation = schemas["RuntimeCorrelationResponse"]

    assert correlation["required"] == ["execution", "traces", "audits", "operator_actions"]
    assert correlation["properties"]["traces"]["$ref"].endswith("/RuntimeCorrelationTracePage")
    assert correlation["properties"]["audits"]["$ref"].endswith("/RuntimeCorrelationAuditPage")

    trace_page = schemas["RuntimeCorrelationTracePage"]
    audit_page = schemas["RuntimeCorrelationAuditPage"]
    assert trace_page["properties"]["items"]["items"]["$ref"].endswith("/WorkflowTraceItem")
    assert audit_page["properties"]["items"]["items"]["$ref"].endswith("/AuditLogItem")


def test_runtime_trace_identifier_exposes_max_length_contract():
    parameters = app.openapi()["paths"]["/api/v1/runtime/correlations/traces/{trace_id}"]["get"]["parameters"]
    trace_parameter = next(parameter for parameter in parameters if parameter["name"] == "trace_id")
    assert trace_parameter["schema"]["minLength"] == 1
    assert trace_parameter["schema"]["maxLength"] == 128


def test_runtime_correlation_does_not_expose_tenant_id_query_parameter():
    for path_item in app.openapi()["paths"].values():
        for operation in path_item.values():
            if not isinstance(operation, dict) or "parameters" not in operation:
                continue
            if operation.get("tags") == ["runtime-audit-trace-correlation"]:
                assert all(parameter["name"] != "tenant_id" for parameter in operation["parameters"])


def test_runtime_trace_identifier_rejects_overlong_value_before_authentication():
    response = client.get(
        "/api/v1/runtime/correlations/traces/" + ("t" * 129),
    )
    assert response.status_code == 422
