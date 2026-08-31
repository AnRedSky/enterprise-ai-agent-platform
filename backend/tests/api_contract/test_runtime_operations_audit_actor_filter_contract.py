"""II-07 Runtime 运维审计操作主体过滤 API Contract 测试。

职责：验证 actor 过滤参数已进入既有 GET 审计查询契约。
边界：只检查公开路由契约，不启动服务，不访问真实数据库。
"""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_runtime_audit_query_exposes_optional_actor_filter():
    route = next(route for route in app.routes if route.path == "/api/v1/runtime/operations/audit/query")
    actor_parameter = next(parameter for parameter in route.dependant.query_params if parameter.name == "actor")
    assert actor_parameter.required is False

    parameters = app.openapi()["paths"]["/api/v1/runtime/operations/audit/query"]["get"]["parameters"]
    actor_schema = next(parameter["schema"] for parameter in parameters if parameter["name"] == "actor")
    assert actor_schema["maxLength"] == 128


def test_runtime_audit_query_keeps_get_only_contract_with_actor_filter():
    routes = {
        (route.path, tuple(sorted(route.methods or [])))
        for route in app.routes
        if route.path == "/api/v1/runtime/operations/audit/query"
    }
    assert routes == {("/api/v1/runtime/operations/audit/query", ("GET",))}
