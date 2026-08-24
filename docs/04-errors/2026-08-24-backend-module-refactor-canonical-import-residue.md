# Backend 模块重构：Canonical Import 残留与循环依赖导致应用与测试无法收集

## 1. 发生时间

2026-08-24

## 2. 问题范围

Workflow 领域完成旧入口物理删除后，调用方仍存在两类迁移残留：

- 生产代码引用已删除的 `app.services.workflow_execution` 与 `app.services.workflow_governance`；
- Canonical import 切换后，`WorkflowExecutionService -> WorkflowRuntime -> app.services.workflow` 又形成新的循环依赖。

## 3. 实际表现

第一阶段本地执行 `uv run python -c "from app.main import app; print('APP_IMPORT_OK')"` 时出现 `ModuleNotFoundError`；Workflow targeted tests、Webhook tests 以及 Backend Regression 在测试收集阶段因此失败。

完成 canonical import 清理后，第二阶段出现：

```text
ImportError: cannot import name 'WorkflowExecutionService' from partially initialized module 'app.services.workflow'
ImportError: cannot import name 'WorkflowRuntime' from partially initialized module 'app.runtime.workflow_runtime'
```

这说明旧入口残留已经清除，但直接把两个高层模块改成互相顶层 import 仍然违反依赖方向。

同时，模块重构 Gate 的目标是旧模块路径必须为 0，因此不能通过重新创建兼容垫片解决。

## 4. 根因

本次 Workflow 完整迁移涉及两个不同层级：

- `WorkflowExecutionService` 是 Workflow 领域服务，负责 Execution / Node Execution 状态机，并委托 Runtime 执行节点；
- `WorkflowRuntime` 是运行时编排层，需要在没有显式注入 Execution Service 的测试/调用场景下创建正式 Workflow Execution Service。

如果两者都在模块加载阶段通过顶层 import 互相依赖，就形成：

```text
services.workflow.__init__
  -> services.workflow.execution
      -> runtime.workflow_runtime
          -> services.workflow
```

因此问题不是缺少业务实现，而是 canonical module migration 后暴露出的循环依赖。

## 5. 修复原则

按照 `docs/01-governance/DEVELOPMENT.md` 与 Backend Module Architecture 的完全重构原则：

1. 生产代码统一使用 `app.services.workflow` 正式入口；
2. 不恢复 `workflow_execution.py`、`workflow_governance.py`、`workflow_registry.py` 等旧入口；
3. 不创建兼容垫片，不复制第二套 Workflow Execution / Governance / Runtime 实现；
4. Runtime 保留 `execution_service` 依赖注入；只有未注入时才在 `execute()` 内延迟解析正式 `app.services.workflow` 入口，从而避免模块初始化循环；
5. 保持 API Contract、数据库结构和 Runtime 业务语义不变；
6. 相关模块继续补充中文职责、边界和关键依赖说明。

## 6. 验证要求

本地必须重新执行：

```powershell
cd backend

git fetch origin
git reset --hard origin/main

git log -3 --oneline

uv run python -c "from app.main import app; print('APP_IMPORT_OK')"

git grep -n -E "app\.services\.workflow_execution|app\.services\.workflow_governance|app\.services\.workflow_registry" -- "*.py"

uv run pytest -q `
  tests/unit/test_workflow_execution_state_machine.py `
  tests/unit/test_workflow_execution_concurrency.py `
  tests/unit/test_workflow_execution_idempotency.py `
  tests/unit/test_workflow_execution_governance.py `
  tests/unit/test_workflow_execution_retry_transition.py `
  tests/unit/test_workflow_governance.py `
  tests/unit/test_workflow_publish_governance.py `
  tests/unit/test_workflow_retry_budget.py `
  tests/unit/test_workflow_retry_policy.py `
  tests/unit/test_workflow_runtime.py `
  tests/unit/test_workflow_runtime_timeout.py `
  tests/unit/test_webhook_trigger.py

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1

uv run pytest -q
```

记录以上命令的实际本地结果；未执行的结果不得标记为通过。