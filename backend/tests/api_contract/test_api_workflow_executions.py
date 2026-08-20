from app.main import app


def test_workflow_execution_routes_are_registered():
    paths = {route.path for route in app.routes}
    assert "/api/v1/workflows/{workflow_id}/executions" in paths
    assert "/api/v1/workflows/executions/{execution_id}/run" in paths
    assert "/api/v1/workflows/executions/{execution_id}" in paths
    assert "/api/v1/workflows/executions/{execution_id}/nodes" in paths
    assert "/api/v1/workflows/executions/{execution_id}/trace" in paths
    assert "/api/v1/workflows/executions/{execution_id}/transition" in paths
    assert "/api/v1/workflows/executions/{execution_id}/nodes/transition" in paths
