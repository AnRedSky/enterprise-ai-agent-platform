# 2026-08-27 Durable Frontier Failure Terminalization Transaction Boundary

## 问题

Durable Frontier Runtime 的异常路径已经在同一补偿事务中锁定 Frontier 与 WorkflowExecution，但原实现调用 `WorkflowExecutionService.transition(..., "failed")`。

该通用领域入口会自行 `commit()`。因此原异常路径实际上可能变成：

```text
Frontier → failed/retry_wait
        ↓
ExecutionService.transition()
        ↓
Execution → failed
        ↓
提前 COMMIT
        ↓
Frontier / retry 状态再提交
```

这与 Durable Frontier 主线要求的 Frontier / Execution failure 原子边界不一致。

## 修复

新增 `_mark_execution_failed_in_transaction()`，只负责在当前 `AsyncSession` 中：

- 校验 Execution 仍允许进入 failed；
- 写入 `failed`、`ended_at`、error code/message；
- 清除 Execution Worker ownership / lease；
- 写入 Governance trace / audit；
- **绝不执行 commit**。

`_converge_failure()` 现在统一由外层：

```text
lock Frontier
lock Execution
        ↓
Frontier retry_wait / failed
        ↓
Execution running → failed（如需要）
        ↓
唯一 COMMIT
```

任何异常都由当前补偿事务整体 rollback。

## 不变量

- 通用 `WorkflowExecutionService.transition()` 仍可用于普通 Runtime / API 生命周期；
- Durable Frontier failure progression 不得调用会自行 commit 的状态入口；
- Frontier 与 Execution failure 必须共享同一数据库事务；
- 已经 failed 的 Execution 不重复写 failure trace / audit；
- stale Worker 仍由 Frontier owner / attempt fencing 阻断。

## Unit Test

新增：

```text
backend/tests/unit/test_frontier_failure_transaction.py
```

覆盖 transaction-local terminalization 与 already-failed 幂等边界。

本轮仅实现 Unit Test，未执行 pytest。
