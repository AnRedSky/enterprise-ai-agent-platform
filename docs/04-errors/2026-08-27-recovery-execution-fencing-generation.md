# 2026-08-27 Recovery Execution Fencing Generation

## 问题

`WorkflowExecution` 已经保存 `worker_owner` 与 `worker_attempt`。Worker 重新 Claim / reclaim 同一 Execution 时会递增 `worker_attempt`，形成新的 fencing generation；但 Execution Domain Service 原先在重新加锁后只比较 `worker_owner`，没有比较 `worker_attempt`。

因此同一个 Worker owner 在 Execution lease 过期并重新 Claim 后，旧的 ORM execution context 仍可能携带旧 generation，却通过 owner-only 校验继续进入状态转换。

## 风险

典型竞争：

```text
Worker A / owner=A / attempt=3
        ↓ lease expired
Worker A or another Worker reclaim
        ↓
owner=A or B / attempt=4
        ↓
旧 Worker A 使用 attempt=3 的 Execution context
```

如果只检查 owner，`owner=A` 的重新 Claim 场景无法识别 stale context；状态转换、Node transition 或其他 Durable 写入可能因此失去严格 fencing。

## 修复

`WorkflowExecutionService._lock_execution()` 现在统一调用 `_validate_execution_fencing()`，同时比较：

- `worker_owner`；
- `worker_attempt` / fencing generation。

只有 owner 与 generation 同时匹配时，已认领 Worker 的 Execution context 才能继续状态转换。

HTTP / 非 Worker 调用保持兼容：当 source context 没有 `worker_owner` 时，不启用 Worker fencing 比较。

## Durable 边界

```text
Execution Claim
    ↓
worker_owner + worker_attempt
    ↓
Runtime / Node transition
    ↓
_lock_execution()
    ↓
FOR UPDATE + owner/generation validation
    ↓
Durable write
```

因此旧 Worker 的 stale generation 在进入 Execution / Node 状态持久化边界前即被拒绝。

Frontier 自身仍继续使用既有 `worker_owner + attempt` fencing；本修复把同一 generation 语义向 Execution Domain 收敛。

## Unit Test

新增覆盖：

- owner + generation 一致时允许继续；
- 同一 owner 但 generation 已变化时拒绝；
- owner 已被其他 Worker reclaim 时拒绝。

当前阶段按开发策略暂停 Full Regression / E2E。Unit Test 已补齐但当前 GitHub API 环境无法实际运行 pytest，因此不得将本轮 Unit Test 标记为 PASS。
