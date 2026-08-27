# 2026-08-27 Durable Frontier Terminalization Transaction Boundary

## 1. 问题

`PlannerDrivenDurableFrontierWorkflowWorker.execute_frontier()` 在调用 `complete_frontier_with_checkpoint()` 后，原先通过 `WorkflowExecutionService.transition(..., "completed")` 完成 Execution terminalization。

`WorkflowExecutionService.transition()` 是面向普通 Execution 生命周期 API 的提交入口，会执行 `db.commit()`。因此在 Durable Frontier 成功路径中存在错误的事务边界：

```text
Frontier → completed
      ↓
frontier_completed Checkpoint → flush
      ↓
Execution.transition(completed)
      ↓
提前 commit
      ↓
外层 Next Frontier / progression 事务边界被破坏
```

这与 Durable Frontier 要求的单一事务不一致。

## 2. 根因

普通 Execution 状态转换和 Durable Frontier progression 的事务职责不同：

- 普通 API / Runtime 状态转换可以由 `WorkflowExecutionService.transition()` 自己提交；
- Durable Frontier completion 必须由 progression primitive 控制事务，确保 Frontier、Checkpoint、Execution terminalization、Next Frontier 同时 commit 或同时 rollback。

直接复用带 commit 的普通入口会让 Durable progression 无法保持原子边界。

## 3. 修复

`complete_frontier_with_checkpoint()` 现在在 `next_identity is None` 的终态路径中：

1. 锁定同 tenant 的 `WorkflowExecution`；
2. 验证当前状态仍为 `running`；
3. 再次验证 Worker owner / fencing generation；
4. 设置 `completed / ended_at / output_data`；
5. 清除 `worker_owner / worker_lease_expires_at`；
6. 写入同一事务的 trace / audit；
7. 最后由调用方统一 `commit()`。

成功路径变为：

```text
NodeExecution completed facts
        ↓
Frontier → completed
        ↓
frontier_completed Checkpoint
        ↓
Execution → completed
        ↓
Next Frontier（若存在）
        ↓
唯一 COMMIT
```

任一阶段失败均由外层事务统一 rollback。

## 4. 边界

该修复只改变 Durable Frontier progression 的 terminalization 事务边界，不改变普通 HTTP Execution 状态转换的既有提交语义，也不创建第二套 Execution 状态机。

## 5. 测试

新增 Unit Test 用于覆盖终态 progression contract；本轮没有执行 pytest，因此不记录 PASS。

## 6. 后续主线

继续验证 Next Frontier、terminal Execution、expired Frontier Recovery、Worker Claim/Fencing 在同一 durable lifecycle 中的收敛关系；完整测试在全部主线任务完成后再启动。
