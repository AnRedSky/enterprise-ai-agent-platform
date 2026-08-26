# E20260826 — Worker 启动触发 Workflow Service 与 Runtime 循环导入

## 现象

在 `main` 最新 Durable Resume Runtime 集成后，直接执行 `uv run python run_worker.py` 在模块初始化阶段失败：

```text
ImportError: cannot import name 'WorkflowRuntime' from partially initialized module 'app.runtime.workflow'
```

失败链路为：

```text
run_worker.py
  -> app.runtime.workflow.runtime
  -> app.services.workflow.checkpoint.recovery.dag_runtime_sequence
  -> app.services.workflow.__init__
  -> app.services.workflow.execution
  -> app.runtime.workflow
```

## 根因

`app.services.workflow.__init__` 在包初始化阶段立即导入 `execution`、`governance`、`registry`。Runtime 为了加载 Durable Resume Sequence Planner 进入 `app.services.workflow` 子包时，会先执行该 `__init__`，而 `execution` 又反向导入 `app.runtime.workflow`，形成循环初始化。

这不是 Durable Resume DAG Contract 本身的问题，而是新增 Runtime integration 后暴露的领域包入口初始化顺序缺陷。

## 修复

将 Workflow 领域入口改为按名称懒加载：

- 保留 `from app.services.workflow import WorkflowExecutionService` 等正式入口；
- 包初始化阶段不再立即加载三个 Service；
- 首次访问具体服务名称时再加载对应领域模块；
- 不增加兼容旧路径、代理实现或第二套 Service；
- 增加 Runtime/Service 双入口导入回归测试，覆盖 Worker 启动暴露的循环依赖边界。

## 验证要求

```powershell
uv run pytest -q tests/unit/test_workflow_imports.py
uv run pytest -q tests/unit/test_workflow_dag_contract.py tests/unit/test_workflow_dag_planner.py tests/unit/test_workflow_dag_runtime.py tests/unit/test_workflow_dag_runtime_sequence.py tests/unit/test_workflow_resume_planner.py tests/unit/test_workflow_runtime_resume.py
uv run pytest -q
uv run pytest -q -W error::RuntimeWarning
uv run python run_worker.py
```

其中 `uv run python run_worker.py` 是启动烟雾测试；服务成功进入 Worker 主循环后应由开发者终止。Real API Durable Resume 仍使用现有 tenant-safe Gate，并要求 API、Scheduler、Worker、PostgreSQL 先由开发者实际启动。
