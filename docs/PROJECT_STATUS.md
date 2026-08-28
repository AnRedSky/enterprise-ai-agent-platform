# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.7 Advanced Workflow Orchestration：主线生产代码持续收口；当前 Real API / Runtime 验证仍需开发者本地重新执行，不标记最终验收通过。
- Phase 2.8-A Multi-Agent Collaboration Contract：已冻结。
- 当前开发任务：**Phase 2.8 Backend Domain + API Contract**，首版 Delegation Contract 已完成；当前优先修复 Phase 2.7 Real API blocker，再进入 Phase 2.8 Runtime Integration。

## 2026-08-28 最新开发者反馈与本轮修复

### Durable Frontier Worker targeted Unit

开发者实际执行：

```text
uv run pytest tests/unit/test_durable_frontier_worker_dispatch.py -q
13 passed in 0.12s
```

该结果证明当前 `main` 的 Claim → Execution `running` 生命周期修复通过 targeted Unit。

### Backend default regression

开发者实际执行：

```text
uv run pytest -q
820 passed, 3 skipped, 42 deselected in 33.35s
```

本结果为本轮开发前的实际本地结果；本轮新增 Real API 测试 Contract 修复提交后必须重新执行，不能沿用该结果作为新提交的 PASS。

### Migration / DB

开发者实际执行：

```text
uv run alembic upgrade head
uv run alembic current
0039_workflow_node_execution_tenant_trigger (head)
```

本结果为本轮测试 Contract 修复前的实际结果；本轮没有新增数据库结构变更，因此仍作为当前数据库基线，但后续提交仍需重新验证 migration Gate。

### Real API 多实例服务边界

Tenant Safe Real API Gate 实际检测到：

- 3 个 Worker 进程；
- 3 个 Scheduler 进程。

当前 Gate 已允许多个 Worker / Scheduler 并发运行，不再要求单实例。该约束与 Durable Frontier PostgreSQL claim / lease / fencing，以及 Scheduler slot claim / idempotency 的真实并发验收语义一致。

### 本轮实际 Real API 失败

开发者在当前 `main` `6227a6c` 实际执行 Tenant Safe Real API Gate：

```text
38 passed / 3 failed
```

三个失败全部集中于 Resume Checkpoint Contract 断言：

1. `test_real_worker_executes_durable_resume_from_checkpoint`
2. `test_real_worker_executes_full_linear_dag_after_resume`
3. `test_real_worker_resume_dag_failure_after_frontier_preserves_checkpoint_and_lease`

实际现象为 Resume 后 NodeExecution 已正确完成，但 Resume Checkpoint 的：

```text
checkpoint_reason = frontier_completed
node_id = NULL
node_status = NULL
```

与测试仍断言的旧 Node-level Checkpoint Contract 不一致。

这不是要求生产代码恢复旧 Node identity 的问题。当前 Phase 2.7 Contract 已明确 `frontier_completed` 是 Execution-level durable fact，不能携带 Node identity/status；上一提交 `0b89944` 又进一步阻止 Durable Frontier Worker 在 `node.completed` 路径重复追加 Node-level Checkpoint，正式完成事实统一由 `complete_frontier_with_checkpoint()` 产生。

### 本轮代码修复

已直接提交 `main`：

- `19879d6` — `test(real-api): align durable resume checkpoint assertions with frontier contract`
- `fbbca42` — `test(real-api): align resume DAG checkpoints with frontier completion contract`

修复内容：

- `test_workflow_resume_api.py` 不再把 Resume Frontier completion 当作 Node-level Checkpoint；
- Resume 单 Frontier 验证 `frontier_completed + frontier_id + node_id=None + node_status=None`；
- Resume 三节点 DAG 验证两个 `frontier_completed` Checkpoint，序号连续且均不携带 Node identity；
- Resume Frontier 成功后下游 Node 再失败的场景验证唯一 `frontier_completed` Checkpoint，并保持 `frontier_id` 存在；
- NodeExecution lineage 仍独立验证 `prepare / provider-call / finish` 的实际状态，不把 Node Fact 与 Execution-level Checkpoint 混为一谈。

以上新提交**尚未由开发者本地重新执行**，因此不得标记 PASS。

## 当前验证状态

### 已实际通过（修复提交之前）

- Durable Frontier Worker targeted Unit：`13 passed`；
- Backend default regression：`820 passed, 3 skipped, 42 deselected`；
- Alembic upgrade head / current：实际成功，当前 head `0039_workflow_node_execution_tenant_trigger`。

### 本轮修复后待重新执行

- Resume / Resume DAG / Resume Failure Real API；
- Runtime Model Governance Real API；
- Usage Accounting Real API；
- Scheduler Real API；
- Tenant Safe Real API 全量 Gate；
- Backend default regression；
- Alembic upgrade head / current；
- Worker / Scheduler 多实例实际生命周期验收。

## 下一执行顺序

```text
1. 同步最新 main
2. uv run pytest tests/unit/test_durable_frontier_worker_dispatch.py -q
3. Resume / Resume DAG / Resume Failure targeted Real API
4. Runtime Governance + Usage Accounting + Scheduler targeted Real API
5. Tenant Safe Real API 全量 Gate
6. uv run pytest -q
7. uv run alembic upgrade head
8. uv run alembic current
9. Worker / Scheduler 多实例实际生命周期验收
10. Phase 2.7 blocker 全部收口后，继续 Phase 2.8 Delegation Runtime Integration
11. 更新 Phase / Acceptance / Status / Error
```

## 本地服务要求

Unit 不需要外部服务。Real API / Runtime / Scheduler 验收需要开发者单独启动：

- PostgreSQL：`localhost:5432`；
- Redis：`localhost:6379`；
- API Service：`127.0.0.1:8000`；
- Worker Service：至少 1 个当前 `main` Worker；允许多个 Worker 并发运行；
- Scheduler Service：至少 1 个当前 `main` Scheduler；允许多个 Scheduler 并发运行；
- Real Provider fixture：由 Real API 测试本地启动；不提交远程 Secret。

测试 Gate 不自动启动或停止服务。