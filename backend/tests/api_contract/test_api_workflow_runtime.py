from app.main import app


def test_workflow_runtime_route_is_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/workflows/executions/{execution_id}/run" in paths
