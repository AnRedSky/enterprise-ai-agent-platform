# 2026-08-28 Phase 2.7 Real API：Durable Frontier 失败 Node Fact 丢失与旧 Runtime Contract 测试漂移

## 1. 实际现象

开发者在 `a26681d`（`main`）执行 tenant-safe Real API Gate，结果：

```text
9 failed, 32 passed in 193.84s
```

其中可归并为两类工程问题：

1. Runtime Model Governance Real API 测试仍创建 `edges: []` 的单节点 Workflow，而当前 Durable Frontier Runtime Contract 已要求合法 DAG 连接，因此运行阶段返回 `DAG Workflow 必须包含非空 edges`。
2. Durable Frontier 在 Runtime Node 失败时，Node 状态与 Frontier completion 共用同一事务。Runtime 异常触发事务 rollback 后，Frontier / Execution failure compensation 会持久化失败状态，但原事务中的 `WorkflowNodeExecution(status=failed)` 同时被回滚，导致 PostgreSQL 中只剩前序已提交 Node / Checkpoint，Resume 无法识别本次失败 Node。

## 2. 根因

### 2.1 Runtime Contract 测试漂移

Real API fixture 沿用了历史单节点空 `edges` Definition。当前 Scheduler / Worker 路径已经以 Durable Frontier 作为真实执行 work item，合法 Workflow 必须形成可规划的 DAG frontier。因此旧测试不再代表当前生产 Contract。

### 2.2 失败 Node Durable Fact 未在补偿事务重建

`PlannerDrivenDurableFrontierWorkflowWorker.execute_frontier()` 中，Node Runtime、Node Checkpoint 与 Frontier completion 在同一事务内执行。任意 Node Runtime 异常都会 rollback；随后 `_converge_failure()` 只处理 Frontier 与 Execution lifecycle，没有重新写入本次失败 Node fact。

这会产生：

```text
prepare completed
provider-call running/failed  -- rollback --> 丢失
Frontier failed              -- 保留
Execution failed             -- 保留
```

因此真实 Resume 验收看到 `prepare` 已完成，却看不到 `provider-call` failed Node。

## 3. 修复原则

- 不创建第二套 Workflow Runtime / Retry / Checkpoint 实现。
- Runtime Governance 测试改为当前合法最小 DAG：`prepare -> governed-agent`。
- Frontier failure compensation 在同一补偿事务内恢复单 Node Frontier 的失败 Node Durable Fact。
- Multi-frontier 失败不猜测具体失败分支，避免错误标记尚未执行的 sibling Node。
- 不新增数据库结构，不改变 API Contract。
- 所有变更直接基于 `main`，保持可追溯原子提交。

## 4. 验证要求

本修复提交前必须在开发者本地执行：

```powershell
cd backend
uv run pytest tests/unit/services/workflow/checkpoint/test_checkpoint_export_fencing.py -q
uv run pytest tests/api_real/test_runtime_model_governance_api.py -q
uv run pytest tests/api_real/test_workflow_resume_api.py tests/api_real/test_workflow_resume_dag_api.py tests/api_real/test_workflow_resume_failure_api.py -q
```

然后执行完整 tenant-safe Real API Gate：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

## 5. 服务前置条件

Real API / Worker 验收前必须确认：

- PostgreSQL `localhost:5432`；
- Redis `localhost:6379`；
- API `127.0.0.1:8000`；
- 至少一个使用当前 `main` 代码启动的 Worker；
- Scheduler 仅在执行 Scheduler 相关验收时启动；
- Real Provider fixture 由测试进程本地启动，不依赖远程真实 Provider。

Gate 不自动启动或停止服务。
