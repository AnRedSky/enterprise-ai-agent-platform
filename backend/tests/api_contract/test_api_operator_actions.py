"""Operator Action API Contract 单元测试。

职责：验证 II-01 新增 HTTP 路由、请求字段与统一操作入口存在。
边界：不启动 API、Scheduler、Worker、PostgreSQL 或 Redis，不执行真实业务动作。
"""

from app.api.v1.runtime.operator_actions import OperatorActionRequest, router


def test_operator_action_routes_are_registered():
    paths = {route.path for route in router.routes}
    assert "/api/v1/runtime/operator-actions/workflow-executions/{execution_id}" in paths
    assert "/api/v1/runtime/operator-actions/workflow-executions/{execution_id}/{action}" in paths
    assert "/api/v1/runtime/operator-actions/workflow-triggers/{trigger_id}" in paths
    assert "/api/v1/runtime/operator-actions/workflow-triggers/{trigger_id}/{action}" in paths


def test_operator_action_request_has_explicit_confirmation_and_payload_defaults():
    request = OperatorActionRequest()
    assert request.confirm is False
    assert request.reason is None
    assert request.input_data == {}
