# 2026-08-27 — Checkpoint Execution Lifecycle Boundary

## 现象

Durable Frontier completion、Execution terminalization、Recovery 与 Checkpoint 持久化存在交叉窗口：Worker 在取得 Execution 行锁前生成的旧上下文可能携带 `running` / `pending` Execution snapshot，而另一个事务已经将同一 Execution terminalize。若 Checkpoint durable write 只校验 Worker owner / fencing，不校验当前 Execution status，就可能把过期生命周期事实继续写入 Checkpoint。

## 根因

Checkpoint Service 的 Durable Write boundary 已经锁定 `WorkflowExecution`，但此前只校验 tenant 与 Worker fencing，`execution_status` 主要被当作待写快照字段，没有强制证明它仍等于锁定行的当前状态。

因此存在：

```text
Worker A stale context
    ↓
requested execution_status=running
    ↓
Execution 已被 Worker B terminalize → completed
    ↓
Checkpoint write
```

## 修复

`WorkflowExecutionCheckpointService.append_next_in_transaction()` 在锁定 Execution、完成 Worker fencing 校验后：

1. 先处理完全相同的 `frontier_completed` 幂等命中；
2. 非幂等命中路径统一调用 `_validate_execution_status_boundary()`；
3. 只有 `execution.status == execution_status` 时才允许创建新的 durable Checkpoint；
4. 状态漂移立即返回 HTTP 409，调用方事务不得继续产生新的 Checkpoint。

## Contract

```text
Lock WorkflowExecution
        ↓
Tenant guard
        ↓
Worker owner / fencing guard
        ↓
Existing idempotent boundary?
   ├── yes → return existing fact
   └── no
        ↓
Current Execution status == requested snapshot status?
   ├── no  → reject 409
   └── yes → allocate sequence → flush Checkpoint
```

该约束与 Frontier Recovery Guard 共同保证：terminal Execution 既不能通过过期 Frontier Recovery 重新激活，也不能通过 stale Worker 的 Checkpoint write 伪造旧生命周期事实。

## 单元测试

新增 `backend/tests/unit/test_workflow_checkpoint_lifecycle.py`，覆盖：

- matching Execution status 正常通过；
- `completed` Execution 拒绝旧 `running` snapshot；
- `failed` Execution 拒绝旧 `pending` snapshot。

当前环境按开发策略暂停实际 pytest 执行，不记录测试 PASS。

## 后续

继续检查 Next Frontier deterministic identity 与 terminalization / Recovery / Claim 的交叉事务，确保同一逻辑 Frontier 不会因重复 completion、Recovery re-entry 或 duplicate Worker consumption 被重新消费。
