"""Workflow 领域服务入口。

职责：提供 Workflow Registry、Execution 与 Governance 的统一懒加载入口。
边界：不承担 API 协议适配、Runtime 节点执行或数据库基础设施实现；通过懒加载避免 Workflow Service 与 Runtime 的循环依赖。
关键依赖：Workflow 领域服务模块及 Python 模块加载机制。
"""

from importlib import import_module

__all__ = ["WorkflowExecutionService", "WorkflowGovernanceService", "WorkflowRegistry"]

_SERVICE_MODULES = {
    "WorkflowExecutionService": ".execution",
    "WorkflowGovernanceService": ".governance",
    "WorkflowRegistry": ".registry",
}


def __getattr__(name: str):
    """按需加载 Workflow 领域服务，避免 Runtime 导入链形成循环依赖。"""
    module_name = _SERVICE_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_name, __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value
