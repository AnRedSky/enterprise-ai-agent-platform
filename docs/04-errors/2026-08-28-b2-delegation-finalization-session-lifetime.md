# B2 Delegation 终态收敛仍停留 running

## 1. 现象

Phase 2.8 B2 Worker Execution Bridge Real Gate 中，Worker Execution 已成功进入 `completed`，且真实 PostgreSQL 查询可以读取 completed Execution 与目标 Agent 输出，但对应 `AgentDelegation.status` 仍为 `running`。

## 2. 根因

此前多次修复只调整了 Delegation completion 的 SQLAlchemy Session 使用方式，却仍然在 `execute_claimed_execution()` 的 Runtime `async with SessionLocal()` 生命周期内部调用 `_finalize_delegation()`。

因此“使用独立 Session”和“Runtime Session 已经结束”被错误地视为同一件事。即使调用 `db.close()`，终态收敛逻辑仍位于外层 Runtime Session 的上下文管理器内部，事务、连接生命周期与 ORM identity 生命周期没有形成真正的代码级边界。

B2 的正确顺序必须是：

```text
Runtime Session
  ↓
Workflow Execution terminalization
  ↓
退出 Runtime Session async with
  ↓
Delegation finalization Session
  ↓
Delegation + AuditLog + Trace 原子提交
```

而不是：

```text
Runtime Session
  ↓
Workflow Execution terminalization
  ↓
close() / finally
  ↓
Delegation finalization
  ↓
仍处于 Runtime Session async with 生命周期
```

## 3. 修复

将 Delegation finalization 从 Runtime Session 的 `finally` 中移出，在 Runtime `async with` 完整退出后再执行 `_finalize_delegation()`。

异常场景不再在 Session 内立即重新抛出，而是先记录 `outcome`、`reason_code` 与待抛异常；Session 关闭后完成 Delegation terminalization，再恢复原有异常传播语义。

这样将“Worker Execution terminalization”和“Delegation terminalization”形成真正的生命周期边界，而不是依赖 `AsyncSession.close()` 的局部补偿。

## 4. 验证要求

必须重新执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\02_worker_execution_bridge_gate.ps1
```

重点验收：

- B2 bridge Unit 全部通过；
- Backend default regression 无新增失败；
- Alembic head 仍为 `0039_workflow_node_execution_tenant_trigger`；
- Real HTTP + PostgreSQL B2 中 `WorkflowExecution.status == completed`；
- `AgentDelegation.status == completed`；
- `AgentDelegation.ended_at` 非空；
- 目标 Agent 与目标 Agent Version 输出保持正确；
- B3 stale generation fencing 不得被本次修复破坏。

本记录不预填通过结果；最终状态以开发者本地实际执行结果为准。