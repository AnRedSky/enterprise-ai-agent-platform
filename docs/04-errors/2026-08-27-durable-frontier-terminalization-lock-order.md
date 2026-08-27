# Durable Frontier Terminalization Lock-order Closure

> 日期：2026-08-27
> 状态：已修复
> 阶段：Phase 2.7-A Durable Recovery Closure

## 1. 问题

Planner-driven Durable Frontier Runtime 在成功路径进入 `execute_frontier()` 后，曾经提前使用 `SELECT ... FOR UPDATE` 锁定 `WorkflowExecution`。

而成功 completion 的统一 durable progression primitive `complete_frontier_with_checkpoint()` 会先锁定 source `WorkflowFrontier`，再锁定关联 `WorkflowExecution`。Failure convergence 也采用 Frontier → Execution 的锁顺序。

因此存在潜在交叉锁顺序：

```text
Success Runtime:
    Execution lock
        ↓
    Frontier lock

Completion / Failure convergence:
    Frontier lock
        ↓
    Execution lock
```

两个并发事务在特定竞争窗口下可能互相等待，形成数据库死锁风险。

## 2. 修复

`backend/app/services/workflow_worker/durable_frontier_execution.py` 的成功 Runtime 路径不再提前锁定 `WorkflowExecution`。

现在 Runtime 阶段只读取 Execution 一致性快照，用于 Planner / Node execution；真正的 durable completion 仍由 `complete_frontier_with_checkpoint()` 在提交前统一取得：

```text
Runtime snapshot read
      ↓
Frontier lock
      ↓
Execution lock
      ↓
Ownership / lease / lifecycle recheck
      ↓
Checkpoint / Next Frontier
      ↓
COMMIT
```

该方式与 failure convergence 保持一致的 Frontier → Execution 锁顺序。

## 3. 为什么不会削弱 fencing

移除 Runtime 初始 Execution 行锁并不等于移除 fencing。

真正的成功 durable write 仍由 progression primitive 重新校验：

- Frontier owner
- Frontier attempt
- Frontier active lease
- Execution owner
- Execution worker epoch
- Execution active lease
- Execution lifecycle

Runtime Entry 在 Node 执行前也已经单独通过 `_verify_frontier_consumption_ownership()` 锁定并证明 Frontier / Execution consumption ownership；该检查负责消费资格，最终 progression 负责 durable commit fencing，两者职责保持分离。

## 4. 测试状态

本轮没有执行 pytest、集成测试、Real API 或 E2E。

因此不得记录 PASS。后续在 Phase 2.7 全部主线完成后统一进行本地测试与验收。
