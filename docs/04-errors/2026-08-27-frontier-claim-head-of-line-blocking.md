# 2026-08-27 Durable Frontier Claim Head-of-Line Blocking

## 1. 问题

Worker Claim 原流程先通过 `_frontier_tenant_candidate()` 按最早 Frontier 选择 tenant，再调用 `claim_next_frontier()` 判断关联 Execution 是否允许当前 Worker Claim。

当最早 Frontier 所属 Execution 仍被其他 Worker 的有效 lease 占用时：

```text
最早 Frontier
    ↓
Tenant A
    ↓
Execution lease 被 Worker-A 持有
    ↓
claim_next_frontier() 无法 Claim
    ↓
return None
    ↓
Tenant B 的可执行 Frontier 被阻塞
```

这不是数据安全问题，但会造成 Scheduler/Worker 的 Head-of-Line Blocking，降低并发吞吐，并使 Recovery 与多 tenant 调度出现不必要的等待。

## 2. 根因

tenant candidate 与实际 Frontier Claim 使用了两套不同的筛选阶段：

1. candidate 只看 Frontier `pending/retry_wait` 与 `available_at`；
2. claim 才检查 Execution status、owner 与 lease。

因此 candidate 可以选择一个最终必然无法 Claim 的 tenant。

## 3. 修复

`backend/app/services/workflow_worker/frontier_runtime.py` 的 `_frontier_tenant_candidate()` 现在直接 JOIN `WorkflowExecution`，并复用与 `claim_next_frontier()` 等价的 Execution eligibility：

- `pending` Execution：owner 为空或 lease 已失效；
- `running` Execution：当前 owner 为本 Worker，或者 Execution lease 已失效。

只有真正存在可安全 Claim Frontier 的 tenant 才能成为 candidate。

## 4. 一致性边界

本修复不放宽 tenant isolation，也不绕过 `claim_next_frontier()` 的最终 Claim 条件。

```text
Tenant candidate
      ↓
Execution eligibility
      ↓
claim_next_frontier()
      ↓
Execution ownership / fencing
      ↓
Frontier claim
```

candidate 只是减少无效查询和 Head-of-Line Blocking；最终安全边界仍由 Durable Frontier Claim transaction 负责。

## 5. 单元测试

新增：

```text
backend/tests/unit/test_frontier_tenant_candidate.py
```

覆盖：

- candidate 查询必须关联 `workflow_executions`；
- 查询必须包含 Worker owner / lease eligibility；
- 无安全可调度 Frontier 时返回 `LookupError`。

本轮没有执行 pytest，不记录测试 PASS。

## 6. 后续

继续沿：

```text
Recovery re-entry
    ↓
Execution lease / Frontier lease convergence
    ↓
Concurrent Worker Claim
    ↓
Duplicate completion
    ↓
Terminalization
    ↓
Replay convergence
```

继续检查多 Worker 并发 Claim 下的 Execution ownership reacquire、Frontier attempt/fencing generation 以及 Recovery re-entry 的单事务一致性。
