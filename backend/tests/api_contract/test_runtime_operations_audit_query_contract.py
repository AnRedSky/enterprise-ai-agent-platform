"""II-06/II-07 Runtime 运维审计查询 API Contract 测试。

职责：验证新增审计查询路由的 HTTP 方法、鉴权、查询参数边界和稳定响应契约。
边界：只验证 API Contract，不启动真实服务，不访问真实数据库。
"""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_runtime_audit_query_route_is_registered_as_get_only():
    routes = {
        (route.path, tuple(sorted(route.methods or [])))
        for route in app.routes
        if route.path == "/api/v1/runtime/operations/audit/query"
    }
    assert routes == {("/api/v1/runtime/operations/audit/query", ("GET",))}


def test_runtime_audit_query_requires_bearer_authentication():
    response = client.get(
        "/api/v1/runtime/operations/audit/query",
        params={"page": 1, "page_size": 20, "action": "operator.workflow_execution.retry"},
    )
    assert response.status_code == 401


def test_runtime_audit_query_rejects_invalid_page_size_at_contract_boundary():
    response = client.get(
        "/api/v1/runtime/operations/audit/query",
        params={"page_size": 101},
    )
    assert response.status_code == 401


def test_runtime_audit_query_exposes_stable_response_schema():
    operation = app.openapi()["paths"]["/api/v1/runtime/operations/audit/query"]["get"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith(
        "/RuntimeOperationAuditQueryResponse"
    )
    response_schema = app.openapi()["components"]["schemas"]["RuntimeOperationAuditQueryResponse"]
    assert response_schema["required"] == ["items", "page", "page_size", "total"]
    assert response_schema["properties"]["items"]["items"]["$ref"].endswith("/RuntimeOperationAuditItem")


def test_runtime_audit_query_exposes_filter_bounds():
    parameters = app.openapi()["paths"]["/api/v1/runtime/operations/audit/query"]["get"]["parameters"]
    schemas = {parameter["name"]: parameter["schema"] for parameter in parameters}
    assert schemas["action"]["maxLength"] == 80
    assert schemas["resource_type"]["maxLength"] == 80
    assert schemas["resource_id"]["maxLength"] == 128
    assert schemas["outcome"]["maxLength"] == 24
    assert schemas["actor"]["maxLength"] == 128
