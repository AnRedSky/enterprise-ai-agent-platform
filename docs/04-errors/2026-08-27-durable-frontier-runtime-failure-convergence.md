# 2026-08-27 Durable Frontier Runtime 异常路径收敛

## 1. 问题

Planner-driven Durable Frontier Worker 已经能够完成正常的 Frontier → Runtime → Checkpoint → Next Frontier 路径，但 Runtime 异常仍需要统一映射到 Durable Frontier 生命周期。若异常只向上抛出而不更新 Frontier / Execution，会依赖 lease 过期恢复，导致 retryable failure 与 terminal failure 的语义不一致。

## 2. 原因分析

Runtime 的 Node Retry 属于单次 Runtime dispatch 内部策略；Durable Frontier Retry 属于跨 Worker 调度的持久化策略。两者不能互相替代。

- Node Retry exhausted 后必须由 Frontier 层决定是否进入 `retry_wait`；
- Planner / Contract / 参数等确定性错误不能通过 Frontier Retry 无限重试；
- retry_wait 时 Execution 必须释放 Worker ownership，保证下一次 Claim 可以重新取得 ownership；
- retry attempt 不能在 scheduling 时提前递增，新的 fencing generation 只能由下一次成功 Claim 产生；
- retry exhausted 后 Frontier 与 Execution 必须共同进入 `failed`。

## 3. 修复方案

`PlannerDrivenDurableFrontierWorkflowWorker` 新增统一异常分类与补偿事务：

```text
Runtime dispatch
      ↓ exception
rollback Runtime transaction
      ↓
classify failure
   ├── transient → retry_wait
   │                 + available_at
   │                 + error facts
   │                 + release Execution ownership
   │
   └── terminal → Frontier failed
                    + Execution failed
```

明确可重试异常：HTTP 408 / 429 / 5xx、网络连接异常、TimeoutError、CircuitOpenError。

明确终态异常：HTTP 4xx（上述 408/429 除外）、Planner frontier mismatch、其他未分类业务异常。

Retry policy 继续读取 Workflow `config.retry_budget`，由 `FrontierRetryPolicy` 统一计算 bounded exponential backoff；不创建新的 Execution / Frontier。

## 4. 事务边界

Runtime 原事务异常后必须先 rollback，避免半完成 Node facts 与 Retry 状态混合提交。随后以新事务重新锁定当前 tenant scope 下的 Frontier 与 Execution，并一次性完成 Retry / Failed 状态及 ownership 释放。

retryable 且未耗尽：

```text
Frontier → retry_wait
Execution ownership → released
COMMIT
```

retry exhausted 或 terminal：

```text
Frontier → failed
Execution → failed
Worker ownership → released
COMMIT
```

## 5. 测试范围

新增 Unit Test 覆盖：

- HTTP 503 → retryable；
- HTTP 409 → terminal；
- `retry_budget` → FrontierRetryPolicy 映射。

本环境未实际执行 pytest，因此不记录 Unit Test PASS。完整 Backend / Frontend / E2E / Real API 测试继续按项目当前阶段策略暂停。
