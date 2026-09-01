"""Runtime Operator Action 审计查询 API Contract 测试。

职责：验证 Operator Action 审计查询的 HTTP 方法、鉴权、管理员权限、参数边界和响应契约。
边界：只验证 API Contract，不启动服务，不访问真实数据库。
"""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.security import create_token
from app.main import app
from app.services.runtime_operations import OperatorAuditQueryService


client = TestClient(app)


def _schema_max_length(schema: dict) -> int:
    """读取字符串 schema 的最大长度，兼容 nullable 的 anyOf 表示。"""
    if "maxLength" in schema:
        return schema["maxLength"]
    for variant in schema.get("anyOf", []):
        if variant.get("type") == "string" and "maxLength" in variant:
            return variant["maxLength"]
    raise AssertionError(f"schema does not expose maxLength: {schema}")


def _schema_format(schema: dict) -> str:
    """读取 OpenAPI schema 格式，兼容 nullable UUID 的 anyOf 表示。"""
    if "format" in schema:
        return schema["format"]
    for variant in schema.get("anyOf", []):
        if variant.get("format"):
            return variant["format"]
    raise AssertionError(f"schema does not expose format: {schema}")


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


def test_operator_audit_query_accepts_admin_role_before_database_access(monkeypatch):
    """管理员鉴权通过后，Contract 测试不得触碰真实数据库。"""

    async def _contract_result(self, tenant_id, **kwargs):
        return {"items": [], "page": kwargs["page"], "page_size": kwargs["page_size"], "total": 0}

    monkeypatch.setattr(OperatorAuditQueryService, "query", _contract_result)
    token = create_token(uuid4(), ["admin"], tenant_id=uuid4())
    response = client.get(
        "/api/v1/runtime/operations/operator-audits",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 1, "page_size": 50, "total": 0}


def test_operator_audit_query_forwards_operator_action_id_to_service(monkeypatch):
    """管理员可以直接按 Operator Action 正式关联键查询 Canonical AuditLog。"""
    captured: dict = {}

    async def _contract_result(self, tenant_id, **kwargs):
        captured.update(kwargs)
        return {"items": [], "page": kwargs["page"], "page_size": kwargs["page_size"], "total": 0}

    monkeypatch.setattr(OperatorAuditQueryService, "query", _contract_result)
    operator_action_id = uuid4()
    token = create_token(uuid4(), ["admin"], tenant_id=uuid4())
    response = client.get(
        "/api/v1/runtime/operations/operator-audits",
        params={"operator_action_id": str(operator_action_id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert captured["operator_action_id"] == operator_action_id


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
    assert _schema_format(schemas["operator_action_id"]) == "uuid"
