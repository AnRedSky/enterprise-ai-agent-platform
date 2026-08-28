# Phase 2.7 本地完整回归：Workflow Contract Drift Round 2

- 日期：2026-08-28
- 阶段：Phase 2.7 本地回归修复
- 来源：开发者 Windows 本地 `backend` 实际执行 `uv run pytest -q`
- 基线：`c6238df` 及其后续 main 测试契约修复

## 实际结果

开发者反馈的最新本地结果：

```text
26 failed, 785 passed, 3 skipped, 41 deselected, 1 warning
```

Targeted Resume、Frontier 与 `scripts/test/workflow/01_resume_runtime_regression.ps1` 均已在本轮反馈中实际通过；失败集中在完整 Unit Regression 中近期 Durable Contract 收口后的旧 fixture / double / 断言漂移。

## 失败分类

1. DAG Decision Trace：AsyncSession `execute()` result double 未提供异步查询结果的 `scalars().all()` 链。
2. DAG Frontier Planner：历史 terminal fixture 使用空 `edges`，不符合当前非空 edges Contract。
3. DAG Multi-frontier / Join：旧测试仍要求无 Checkpoint 时进行 Join conflict merge；当前 Contract 明确无 Branch Checkpoint 不得声明 Join ready。
4. DAG Join Executor：测试直接保存 executor 输入对象，随后生产代码执行器修改该对象，导致断言被后续 mutation 污染。
5. DAG Resume：NodeExecution tenant boundary fixture 缺少 `tenant_id`。
6. Worker fencing / terminalization：测试 double 缺少 `worker_attempt`、tenant scope 与 Frontier 查询接口。
7. Checkpoint lifecycle：frontier completion collection query、Execution status、node identity 等测试 fixture 未跟随正式 Contract 更新。
8. Automatic Recovery：Checkpoint lineage 缺少 `execution_id`；telemetry attempt 断言未过滤 trace start/finish；Resume outcome callback 缺少 `commit=False` 参数。
9. Resume API：HTTP route test double 未提供真实 commit 边界。
10. Frontier Repository：Claim 已收口为 Execution → Frontier 锁序，旧测试只提供单次查询 result。
11. Recovery lifecycle：Incomplete Resume 已由“永久拒绝”收口为同一事务内可安全 reconcile，旧测试仍期待 reject。
12. Checkpoint tenant boundary：`db.add()` 是同步 Session 操作，旧测试使用 `AsyncMock` 造成 RuntimeWarning。

## 本轮已实施修复

- 对齐 DAG Decision、Checkpoint、Frontier Claim、Worker fencing、Recovery、Resume API 等测试 double 的当前异步查询、tenant、worker epoch、事务与 lineage Contract。
- 对齐 terminal DAG definition 与非空 edges Contract。
- 将 Multi-frontier 无 Checkpoint 的旧 conflict 断言改为“不得声明 Join ready”的正式语义。
- 对 Join executor 输入状态做测试快照，避免 executor mutation 污染输入断言。
- 对 Automatic Recovery telemetry 按 `RECOVERY_ATTEMPT` 事件进行精确断言，并补齐 `commit=False` callback。
- 将 Incomplete Resume 测试改为验证 Durable Bootstrap reconcile，而不是继续期待旧 reject 语义。
- 将 Checkpoint tenant boundary 测试的 Session double 拆分为同步 `add()` 与异步 `execute()/flush()`，消除 RuntimeWarning。

## 验证状态

本轮修复提交后尚未由开发者重新执行 Windows 本地完整回归，因此**不得标记 PASS**。下一步必须以开发者本地实际执行结果为准。
