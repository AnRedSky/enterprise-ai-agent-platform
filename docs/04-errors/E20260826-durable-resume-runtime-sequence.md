# E20260826 — Durable Resume 已创建但 Runtime 未消费 DAG Resume Frontier

## 现象

Durable Resume 的 `WorkflowExecutionService.resume_from_latest_checkpoint()` 已经能够基于 Checkpoint 创建新的 `pending` Resume Execution，但此前 `WorkflowRuntime.execute()` 仍然按照 Workflow Version 的完整 `nodes` 顺序执行。

因此对于：

```text
prepare -> provider-call
```

Source 在 `provider-call` 失败并留下 `prepare` Checkpoint 后，Resume Execution 会再次从 `prepare` 开始，而不是从 Checkpoint frontier 的 `provider-call` 开始。这会破坏 Durable Resume 的核心语义，并可能重复执行已经持久化成功的 Node。

## 根因

此前已完成的 DAG Resume Contract 只存在于纯内存 Planner 层：

1. `WorkflowDagResumePlanner` 计算 frontier；
2. `WorkflowDagResumeRuntimePlanner` 收敛单 frontier；
3. `WorkflowDagResumeRuntimeSequencePlanner` 将单 frontier DAG 展开成确定性线性 Node 序列；
4. 但正式 `WorkflowRuntime` 没有读取 Source Execution 的持久化 completed Node facts，也没有消费 Sequence Planner。

因此 Contract 已冻结，Runtime integration 尚未闭环。

## 修复边界

本次修复只允许 Runtime 从 Source Execution 的持久化 `WorkflowNodeExecution(status=completed)` 集合推导 Resume frontier：

- Resume Execution 的 `input_data` 继续使用 Checkpoint state；
- Source Execution 的 completed Node ID 是唯一的 Resume completion fact；
- Sequence Planner 负责确定性拓扑展开；
- 多 frontier 直接返回 HTTP 409，不能隐式进行分支 state merge；
- 无剩余 frontier 直接返回 HTTP 409，避免错误地把已完成 Resume 标记为 completed；
- 普通非 Resume Execution 完全保持原有顺序 Runtime 行为；
- 不读取或修改 Source Checkpoint；
- 不改变 Worker ownership claim 语义。

## 验证要求

### 单元测试

```powershell
uv run pytest -q `
  tests/unit/test_workflow_dag_contract.py `
  tests/unit/test_workflow_dag_planner.py `
  tests/unit/test_workflow_dag_runtime.py `
  tests/unit/test_workflow_dag_runtime_sequence.py `
  tests/unit/test_workflow_resume_planner.py `
  tests/unit/test_workflow_runtime_resume.py
```

### 全量回归

```powershell
uv run pytest -q
uv run pytest -q -W error::RuntimeWarning
```

### Durable Resume 真实验收

保持 API、Scheduler、Worker、PostgreSQL 由开发者手动管理，然后执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\api-real\05_run_durable_resume_real_tests.ps1
```

该 Gate 会创建 tenant-safe context，并在同一个上下文中验证：

1. Source failed 后存在持久化 Checkpoint；
2. Resume Execution 通过正式 `WorkflowExecutionService` 创建；
3. 独立 Worker 领取 Resume；
4. Runtime 只执行 Checkpoint frontier 之后的 Node；
5. 成功 Resume 产生新的 Node Checkpoint；
6. Resume 再次失败时保持 source lineage，且不伪造新的 completion Checkpoint。

直接执行 `tests/api_real/*.py -m real_api` 而没有 Gate 注入的 `ORGANIZATION_ID` / `ACCESS_TOKEN` 时，测试现在会标记为 skipped，而不是把“缺少验收上下文”误报为产品测试失败。