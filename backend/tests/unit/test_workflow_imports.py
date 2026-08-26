"""验证 Workflow Runtime 与 Workflow Service 入口可以独立初始化。"""


def test_workflow_runtime_import_does_not_trigger_service_cycle() -> None:
    """验证 Worker 启动所需的 Workflow Runtime 导入不会因领域入口初始化产生循环依赖。"""
    from app.runtime.workflow import WorkflowRuntime
    from app.services.workflow import WorkflowExecutionService

    assert WorkflowRuntime.__name__ == "WorkflowRuntime"
    assert WorkflowExecutionService.__name__ == "WorkflowExecutionService"
