# Recovery Checkpoint Stale Worker Late-Write 防护

日期：2026-08-27

## 问题

Recovery Execution fencing 已经在 Execution 状态转换入口校验 `worker_owner + worker_attempt`，Frontier 也有独立的 owner/generation fencing。但 Checkpoint 是不可变 Durable Fact，如果只依赖调用方先前完成的 Frontier fencing，而 Checkpoint Service 自身没有再次验证 Execution generation，则直接调用 Checkpoint 持久化入口时仍可能绕过 Execution-level stale Worker 边界。

## 根因

`WorkflowExecutionCheckpointService.append_next_in_transaction()` 会锁定目标 `WorkflowExecution` 并分配新的 Checkpoint sequence，但此前没有把 Worker 上下文中的 owner / attempt 与锁定后的 Execution generation 做二次比对。

因此理论上存在：

```text
Worker A context: owner=A, attempt=3
          ↓
Execution 被重新 Claim / reclaim
          ↓
locked Execution: owner=A, attempt=4
          ↓
旧 context 仍尝试 append Checkpoint
```

如果只依赖 owner，旧 Worker 在同一 owner 重新 Claim 的情况下可能继续写入 Durable Fact。

## 修复

Checkpoint Service 增加统一 `_validate_worker_fencing()`：

```text
expected_worker_owner
+
expected_worker_attempt
        ↓
SELECT FOR UPDATE Execution
        ↓
locked worker_owner + worker_attempt
        ↓
完全一致 → 允许 append
不一致   → HTTP 409，拒绝 Durable 写入
```

Frontier progression 的唯一成功持久化入口 `complete_frontier_with_checkpoint()` 现在把当前 Frontier 的 `worker_owner + attempt` 原样传入 Checkpoint Service，形成：

```text
Frontier fencing
      ↓
Execution fencing
      ↓
Checkpoint fencing
      ↓
Next Frontier enqueue
```

全部仍处于同一外层事务中。

## 边界

- 未提供 Worker fencing 参数的通用直接 Checkpoint API 保持兼容，适用于非 Worker-owned 的内部调用。
- 一旦调用方提供 `expected_worker_owner`，必须同时提供 `expected_worker_attempt`。
- stale generation 或 reclaimed owner 均拒绝写入。
- 本修复不创建第二套 fencing 机制；Checkpoint 只复用 Workflow Execution 已存在的 `worker_owner + worker_attempt` generation。

## 验证

新增 Unit Test 覆盖：

1. owner + generation 完全匹配时允许继续。
2. 同一 owner 但 generation 已变化时拒绝。
3. owner 已被其他 Worker reclaim 时拒绝。
4. fencing 参数不完整时拒绝。

当前按开发阶段策略暂停 Full Regression、Real API 与 E2E；本轮仅实现并补充 Unit Test，不将未实际执行的测试记录为通过。
