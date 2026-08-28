# Phase 2.7 本地完整回归：Workflow Contract Drift

- 日期：2026-08-28
- 阶段：Phase 2.7 本地回归修复
- 来源：开发者本地 `backend` 实际执行 `uv run pytest -q`
- 基线：`c006419` 及其后续 main 修复；本记录对应开发者反馈中的完整回归结果。

## 实际结果

```text
44 failed, 767 passed, 3 skipped, 41 deselected
```

Targeted Resume、Frontier 与 `scripts/test/workflow/01_resume_runtime_regression.ps1` 已在此前本地结果中达到通过；本轮问题集中在完整 Backend Unit Regression 对近期 Durable Contract 收口后的旧 fixture / double 假设。

## 失败分类

### 1. Resume / API transaction contract

- 不完整 Resume fixture 缺少 `status` / `worker_owner`，无法进入新的 reconcile contract。
- Resume API fake service 未接受 `commit=False`。
- Resume 创建测试未提供 `begin_nested()` transaction double。

### 2. Recovery / Trace lineage

- Recovery Trace fixture 的 Source Execution 缺少 `workflow_version_id`。
- `get_trace_id()` fixture 未提供 workflow-version scope。
- DAG Decision 测试将 `AsyncMock.execute()` 的 coroutine 当作同步 Result，未构造 `scalars().all()` 的真实 double。
- Automatic Recovery fixture 的 `latest_recovery_fact()` 签名仍是旧版，未接受 `tenant_id`。
- Active Worker rejection 测试暴露出生产实现先读取 Checkpoint、再执行 Worker eligibility 判断的问题。

### 3. Scheduler scan lifecycle

- Scheduler 已先独立执行 expired Frontier reclaim，再执行 failed Execution discovery；旧测试的 Session sequence 仍按旧查询顺序构造，导致 candidate 数量与 trace event 断言错位。

### 4. Checkpoint lifecycle / frontier identity

- `frontier_completed` 现在强制要求 `source Frontier` identity；旧测试未提供 `frontier_id`。
- Checkpoint boundary query 返回 collection，旧 double 仍返回 scalar。
- Checkpoint append 现在先锁定并校验 Execution lifecycle，旧 fixture 缺少 `status`、worker epoch 等字段。
- 旧测试使用不存在的 `node_completed` reason，正式 Contract 为 `node.completed`。

### 5. DAG runtime contract

- Multi-frontier Join readiness 已明确要求 Branch Checkpoint callback；无 checkpoint writer 时不得声明 Join ready。
- Runtime DAG Resume 的 NodeExecution 查询现在必须通过所属 Execution 验证 tenant boundary，旧 fixture 缺少 `tenant_id`。
- DAG definition / frontier planner 已拒绝不满足正式 edges Contract 的历史 fixture。

## 已实施修复

- Automatic Recovery 在 `failed + active worker` 场景下先执行硬拒绝，避免无效读取 Durable Checkpoint。
- Resume / Recovery / Trace fixture 补齐新的 tenant、workflow-version、status、worker ownership、transaction 与 commit contract。
- Scheduler fixture 对齐 expired Frontier reclaim → discovery → per-execution recovery 的真实 Session 生命周期。
- Checkpoint fixture 对齐 `frontier_id`、collection query、Execution lifecycle 与 worker epoch Contract。
- DAG Executor 测试对齐“Checkpoint 完成后才 Join ready”的正式语义。
- Resume API fake service 对齐 `commit=False` 原子事务调用。

## 验证状态

以上代码 / 测试修复均已直接提交 `main`，但当前环境不能执行用户 Windows 本地 `uv` / PostgreSQL / Redis 服务，因此**不得把这些修复标记为 PASS**。

下一步必须由开发者拉取最新 `main` 后重新执行：

1. Resume targeted；
2. Frontier targeted；
3. `scripts/test/workflow/01_resume_runtime_regression.ps1`；
4. `uv run pytest -q`；
5. 若完整回归为 PASS，再执行 Alembic head verification 与 Tenant Safe Real HTTP API Gate；
6. Real API Gate 通过后进入 Scheduler / Worker 生命周期手动场景和 Frontend / Browser 独立 Gate。
