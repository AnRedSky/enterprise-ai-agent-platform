"""批量 Operator Action API Contract 测试。

职责：验证批量运维接口的 HTTP 路由、请求字段和响应契约。
边界：不启动服务、不访问真实数据库、不执行真实 Workflow / Trigger 生命周期。
"""

from app.api.v1.runtime.batch_operator_actions import BatchOperatorActionRequest
from app.main import app


def _route(path: str, method: str):
    return next(
        route for route in app.routes
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set())
    )


def test_batch_operator_action_route_is_registered():
    route = _route("/api/v1/runtime/operator-actions/batch", "POST")
    assert route is not None
    assert route.response_model.__name__ == "BatchOperatorActionResponse"


def test_batch_operator_action_request_contract_exposes_tenant_free_payload():
    schema = BatchOperatorActionRequest.model_json_schema()
    assert "tenant_id" not in schema["properties"]
    assert set(schema["properties"]) >= {
        "resource_type", "action", "resource_ids", "confirm", "reason", "input_data",
    }
    assert schema["properties"]["resource_ids"]["maxItems"] == 100
