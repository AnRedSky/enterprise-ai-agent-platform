"""领域包初始化边界回归测试。

职责：验证 Trigger 与 Scheduler 领域包可以独立初始化，避免包级导入形成循环依赖。
边界：只验证 Python 模块加载边界，不启动数据库、API、Worker 或 Scheduler 服务。
"""

from importlib import import_module


def test_trigger_and_scheduler_packages_have_no_import_cycle():
    """验证 Trigger 与 Scheduler 包初始化不会互相触发未完成模块导入。"""
    trigger_module = import_module("app.services.trigger")
    scheduler_module = import_module("app.services.workflow_scheduler")

    assert trigger_module.WorkflowTriggerService is not None
    assert scheduler_module.ScheduledTriggerScheduler is not None
