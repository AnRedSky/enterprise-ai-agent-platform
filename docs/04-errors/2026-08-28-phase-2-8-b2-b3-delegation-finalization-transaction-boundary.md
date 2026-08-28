# Phase 2.8 B2/B3 Worker Delegation 终态收敛事务边界问题

## 1. 发现时间

2026-08-28

## 2. 发现 Gate

- Phase 2.8 B2 Worker Execution Bridge Real Gate
- Phase 2.8 B3 Delegation Completion/Fencing Real Gate

## 3. 实际现象

最新 `main` 在修复 Model Profile Snapshot Fixture 后，B2/B3 已经能够完成 Target Agent Runtime 执行，`WorkflowExecution.status` 持久化为 `completed`，但 B2 Real Gate 最终发现：

```text
assert persisted.status == "completed"
E AssertionError: assert 'running' == 'completed'
```

B3 复用同一真实执行路径，因此同时受到影响。

上一轮已经解决的：

```text
Delegation model profile 与目标 Agent version 不一致
```

不再是本轮故障原因。

## 4. 第一阶段根因与修复

`execute_claimed_execution()` 原先在 Worker Runtime 的 `finally` 阶段调用 `_finalize_delegation()`，而 `_finalize_delegation()` 又重新创建独立的 `SessionLocal()`。

Worker Runtime 使用的 `WorkflowExecutionService.transition()` 会在 Execution terminalization 时提交当前 Worker Session 的事务。Delegation completion/failure 却通过另一个数据库 Session 读取 Worker Execution，并在 Runtime 事务生命周期交界处执行。

第一阶段已将 `_finalize_delegation()` 改为复用 Worker Runtime 当前 `AsyncSession`，并继续使用 commit 前快照的 `worker_execution_id` 防止 `expire_on_commit` 导致隐式异步 IO。

## 5. 第二阶段修复

本地反馈表明第一阶段修复后仍出现：

```text
WorkflowExecution.status == "completed"
AgentDelegation.status == "running"
```

因此 Delegation completion/failure Service 进一步强化为**带完整 fencing 条件的数据库终态写入**：

```text
UPDATE agent_delegations
SET status = completed / failed,
    ended_at = ...,
    error_code = ...,
    error_message = ...
WHERE id = delegation_id
  AND tenant_id = tenant_id
  AND status = running
  AND worker_execution_id = current_worker_execution_id
```

并要求 `rowcount == 1`；否则立即返回 409，拒绝把 stale Worker generation 当作成功完成。AuditLog、WorkflowTraceEvent 与该状态写入继续在同一事务提交。

这样将“状态校验”和“终态 durable write”绑定到同一数据库条件，避免仅依赖 ORM identity state 承载最终 fencing 写入。

## 6. 修复提交

- `796c29ad` — `fix(worker): finalize delegation in active runtime session`
- `5676fff` — `fix(worker): finalize delegation in active runtime session`
- `036868ac` — `fix(delegation): persist terminal state with fenced update`

其中前两个提交解决 Worker Runtime Session / SQLAlchemy 查询问题；`036868ac` 进一步将 Delegation terminal state 写入收敛为带 tenant + running status + Worker generation 的 SQL fencing update。

## 7. 验证要求

必须由开发者本地实际执行，不以 GitHub Actions 结果替代：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\02_worker_execution_bridge_gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\03_delegation_completion_gate.ps1
```

验收重点：

1. B2 Target Agent Runtime 完成后 `WorkflowExecution.status == completed`；
2. 同一 Worker generation 对应 `AgentDelegation.status == completed`；
3. `ended_at` 已持久化；
4. B3 stale Worker generation 仍不能完成当前 Delegation；
5. Backend regression 与 migration/head verification 不回归。

在本地 Gate 尚未执行并反馈前，不得将 B2/B3 Real Gate 标记为通过。
