# 2026-08-28 Phase 2.7：Resume Checkpoint Node Fact Contract 漂移

## 1. 实际现象

开发者在 `main` `6227a6c` 执行 Tenant Safe Real API Gate，得到：

```text
38 passed / 3 failed
```

失败测试：

- `test_real_worker_executes_durable_resume_from_checkpoint`
- `test_real_worker_executes_full_linear_dag_after_resume`
- `test_real_worker_resume_dag_failure_after_frontier_preserves_checkpoint_and_lease`

共同断言失败：

```text
expected node_id / node_status
actual node_id=None / node_status=None
```

## 2. 根因

上一轮 Durable Frontier completion 收口后，`frontier_completed` 被正式定义为 Execution-level Durable Fact：

```text
Frontier completion
    ↓
WorkflowExecutionCheckpoint
    ├── checkpoint_reason = frontier_completed
    ├── frontier_id = source Frontier identity
    └── node_id / node_status / node_attempt = NULL
```

`WorkflowExecutionCheckpointService.append_next_in_transaction()` 已强制拒绝 `frontier_completed` 携带 Node identity/status/input/output；同时，当 Durable Frontier Worker 通过 `node.completed` 路径执行时，不再追加第二条 Node-level Checkpoint，避免同一个 Frontier 同时产生 Node completion fact 与 Execution completion fact。

因此生产实现的持久化结果符合当前 Phase 2.7 Contract，旧 Real API 测试仍按照历史 Node-level Checkpoint Contract 读取 Resume Checkpoint，形成测试与生产 Contract 漂移。

## 3. 修复

已直接更新 `main`：

- `19879d6`：Resume 单 Frontier Real API 改为验证 `frontier_completed`、`frontier_id` 存在以及 Node identity/status 为空；NodeExecution lineage 独立验证。
- `fbbca42`：Resume DAG / Resume Failure Real API 改为验证 `frontier_completed` Checkpoint 序号、Frontier identity 与 Node identity/status 解耦。
- `b44d823`：同步更新项目状态，明确本轮修复尚未由开发者重新执行。

本修复不恢复旧 Node-level Checkpoint，也不修改 Durable Frontier completion 生产边界。

## 4. 设计不变量

```text
NodeExecution.completed
        ↓
Node durable fact
        ↓
Durable Frontier progression
        ↓
frontier_completed Checkpoint
        ↓
Execution-level recovery boundary
```

NodeExecution 仍然保存真实 Node 状态；Checkpoint 只在对应层级记录正式 Durable progression fact。Recovery / Resume 必须根据 Checkpoint reason 区分 Node fact 与 Execution fact，不能通过空 Node 字段猜测 Node identity。

## 5. 验证要求

修复后必须由开发者本地实际执行：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend

uv run pytest tests/unit/test_durable_frontier_worker_dispatch.py -q

uv run pytest `
  tests/api_real/test_workflow_resume_api.py `
  tests/api_real/test_workflow_resume_dag_api.py `
  -q -m real_api

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1

uv run pytest -q

uv run alembic upgrade head
uv run alembic current
```

以上结果在开发者重新执行前不得记录为 PASS。