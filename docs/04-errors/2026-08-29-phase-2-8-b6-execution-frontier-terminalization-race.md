# Phase 2.8 B6：Execution 与 Frontier 终态收敛竞态

## 1. 现象

本地 `06_delegation_multi_worker_runtime_gate.ps1` 的 Unit/Contract、Backend Regression 与 Alembic head 均通过，但 Real HTTP + PostgreSQL 验收出现：

- 多 Worker Delegation 在等待窗口内无法进入终态；
- B2 Worker Execution Bridge 执行后 `WorkflowExecution.status` 仍为 `running`；
- 之前的 stale Frontier asyncpg/Proactor warning 已由 ownership pre-check 修复，不属于本次根因。

## 2. 根因

Durable Frontier Worker 的执行链路中，`WorkflowRuntime.execute()` 在所有 Node 完成后会调用 `WorkflowExecutionService.transition(..., "completed")`。与此同时，当前 Worker 的 Durable Frontier 仍处于 `running`。

`WorkflowExecutionService` 原有 terminalization guard 明确禁止存在活动 Frontier 时进入 Execution terminal 状态，因此 Runtime completion 在该检查处被拒绝。异常发生在 Runtime Session 内，随后事务回滚；Delegation 独立终态收敛也无法取得 `completed` durable fact，最终表现为 Execution/Delegation 长时间保持 `running`。

这形成了错误的顺序依赖：

```text
Runtime 完成 Node
    ↓
Execution -> completed
    ↓
Frontier -> completed
```

而原有 guard 又要求：

```text
Frontier 必须先 completed
    ↓
Execution 才允许 completed
```

两者互相阻塞。

## 3. 修复

将当前 Worker 正在执行的唯一 `running` Frontier terminalization 纳入 `WorkflowExecutionService.transition()` 的同一数据库事务：

1. 先锁定 Execution；
2. 检查活动 Frontier 集合；
3. 仅允许唯一、`running`、owner 一致、attempt 一致且 lease 仍有效的 Frontier；
4. 将该 Frontier 写入与 Execution 相同的终态；
5. 清理 Frontier ownership/lease；
6. 最后写入 Execution terminal 状态并一次提交。

`pending` / `retry_wait` / `claimed` Frontier，以及多个活动 Frontier 仍然拒绝 terminalization，避免错误关闭尚未执行的 sibling Frontier。

## 4. 验证要求

必须至少执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_execution_frontier_terminalization.py
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\06_delegation_multi_worker_runtime_gate.ps1
```

Real Gate 必须再次确认：

- B2 Worker Execution Bridge 的 Execution 进入 `completed`；
- Delegation 进入 `completed` / `failed` / `cancelled` 终态；
- 多 Worker 每个 Delegation 只产生一个 Worker Execution execution fact；
- Frontier 与 Execution 不再出现 terminal/running 分叉；
- 测试输出无新增 RuntimeWarning。

## 5. 边界

本修复不新增第二套 Runtime、Delegation completion 或 Frontier 状态机；仍由现有 Execution Service、Durable Frontier repository 与 Runtime Entry 共同完成正式状态收敛。