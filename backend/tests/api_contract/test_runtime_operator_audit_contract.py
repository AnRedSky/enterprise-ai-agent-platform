"""Runtime Operator Action 审计查询 API Contract 测试。

职责：验证 Operator Action 审计查询的 HTTP 方法、鉴权、管理员权限、参数边界和响应契约。
边界：只验证 API Contract，不启动服务，不访问真实数据库。
"""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.security import create_token
from app.main import app


client = TestClient(app)


def _schema_max_length(schema: dict) -> int:
    """读取字符串 schema 的最大长度，兼容 nullable 的 anyOf 表示。"""
    if "maxLength" in schema:
        return schema["maxLength"]
    for variant in schema.get("anyOf", []):
        if variant.get("type") == "string" and "maxLength" in variant:
            return variant["maxLength"]
    raise AssertionError(f"schema does not expose maxLength: {schema}")


def test_operator_audit_query_route_is_registered_as_get_only():
    routes = {
        (route.path, tuple(sorted(route.methods or [])))
        for route in app.routes
        if route.path == "/api/v1/runtime/operations/operator-audits"
    }
    assert routes == {("/api/v1/runtime/operations/operator-audits", ("GET",))}


def test_operator_audit_query_requires_bearer_authentication():
    response = client.get("/api/v1/runtime/operations/operator-audits")
    assert response.status_code == 401


def test_operator_audit_query_requires_admin_role():
    token = create_token(uuid4(), ["user"], tenant_id=uuid4())
    response = client.get(
        "/api/v1/runtime/operations/operator-audits",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_operator_audit_query_accepts_admin_role_before_database_access():
    token = create_token(uuid4(), ["admin"], tenant_id=uuid4())
    response = client.get(
        "/api/v1/runtime/operations/operator-audits",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code != 403


def test_operator_audit_query_rejects_invalid_page_size_at_contract_boundary():
    response = client.get("/api/v1/runtime/operations/operator-audits", params={"page_size": 101})
    assert response.status_code == 401


def test_operator_audit_query_exposes_stable_response_schema():
    operation = app.openapi()["paths"]["/api/v1/runtime/operations/operator-audits"]["get"]
    response_ref = operation["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
    assert response_ref.endswith("/OperatorAuditQueryResponse")
    response_schema = app.openapi()["components"]["schemas"]["OperatorAuditQueryResponse"]
    assert response_schema["required"] == ["items", "page", "page_size", "total"]
    assert response_schema["properties"]["items"]["items"]["$ref"].endswith("/OperatorAuditItem")


def test_operator_audit_query_exposes_filter_bounds():
    parameters = app.openapi()["paths"]["/api/v1/runtime/operations/operator-audits"]["get"]["parameters"]
    schemas = {parameter["name"]: parameter["schema"] for parameter in parameters}
    assert _schema_max_length(schemas["action"]) == 100
    assert _schema_max_length(schemas["resource_type"]) == 50
    assert _schema_max_length(schemas["resource_id"]) == 100
    assert _schema_max_length(schemas["status"]) == 20
    assert _schema_max_length(schemas["trace_id"]) == 64
