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

## 4. 根因分析

`execute_claimed_execution()` 原先在 Worker Runtime 的 `finally` 阶段调用 `_finalize_delegation()`，而 `_finalize_delegation()` 又重新创建独立的 `SessionLocal()`。

Worker Runtime 使用的 `WorkflowExecutionService.transition()` 会在 Execution terminalization 时提交当前 Worker Session 的事务。Delegation completion/failure 却通过另一个数据库 Session 读取 Worker Execution，并在 Runtime 事务生命周期交界处执行。

这种设计使 Delegation finalize 与 Worker Runtime 的提交边界发生不必要的 Session 解耦：Delegation 终态收敛依赖另一个 Session 观察当前 generation 的 terminal Execution，而 Worker 本身已经拥有完成该状态机所需的正式 AsyncSession。

此前为解决 AsyncSession `expire_on_commit` 引入的 generation identity snapshot 只能避免 expired ORM 属性的隐式 IO，不能解决 finalize 与 Runtime 使用独立 Session 带来的事务可见性边界问题。

## 5. 修复方案

将 `_finalize_delegation()` 改为接收并复用 `execute_claimed_execution()` 当前的 `AsyncSession`：

```text
Worker Runtime Session
        │
        ├── WorkflowExecution terminal transition
        │       └── commit
        │
        └── Delegation finalize
                ├── SELECT current Worker Execution
                ├── generation fencing
                ├── completed / failed
                ├── AuditLog
                └── WorkflowTraceEvent
```

同时继续使用提前快照的 `worker_execution_id` 作为不可变 generation identity，避免 Runtime 内 commit 后访问 expired ORM identity。

修复保持以下边界不变：

- 不新增 Worker Runtime；
- 不新增 Lease / Retry / Recovery 实现；
- 不绕过 `validate_worker_fence()`；
- 不修改父 Workflow Execution；
- 不削弱 Target Agent Version / Model Profile snapshot 校验；
- Delegation completion/failure 仍由正式 completion Service 执行；
- AuditLog 与 WorkflowTraceEvent 仍在 Delegation completion/failure 事务中持久化。

## 6. 修复提交

- `796c29ad` — `fix(worker): finalize delegation in active runtime session`
- `5676fff` — `fix(worker): finalize delegation in active runtime session`

其中 `5676fff` 仅修正首次代码提交中的 SQLAlchemy 查询括号问题，最终 `main` 应以该提交后的代码为准。

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
