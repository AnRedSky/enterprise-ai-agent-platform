# Phase 1.9 — Runtime Reliability / Production Hardening

> 状态：进行中
> 基线：最新 `main`

## 1. 阶段目标

在 Phase 1.3～1.8 已形成 Model Gateway、Tool Runtime、Memory、Observability、Knowledge/RAG、Workflow/Governance、Scheduler/Webhook Trigger 能力的基础上，进行跨领域 Runtime Reliability 收口。

本阶段不新增新的产品领域，重点验证并修复已经存在的生产一致性、并发、失败恢复、Real API 与跨层联调边界。

## 2. 当前能力基线

| 能力 | 当前判断 |
|---|---|
| Identity / JWT / RBAC / Tenant | 已实现当前历史范围 |
| Agent / AgentVersion / Publish | 已实现当前历史范围 |
| Agent Chat / Model Gateway | 已实现当前历史范围 |
| Tool Registry / HTTP Tool / 安全边界 | 已实现当前历史范围 |
| Memory / Runtime Context | 已实现当前历史范围 |
| Observability / Audit / Trace | 已实现当前历史范围 |
| Knowledge / Ingestion / Retrieval | 已实现当前历史范围 |
| Vector / Hybrid Retrieval | 已实现当前代码范围；真实语义质量仍需真实 Provider 评估 |
| Workflow / Execution / Governance | 已实现当前历史范围 |
| Retry / Timeout / Idempotency / Deadline | 已实现当前历史范围；本阶段继续验证跨边界语义 |
| Circuit Breaker | 1.9-A 代码修复及本地 Gate 已完成；1.9-B 继续验证跨 worker / stale Probe 边界 |
| Scheduled Trigger | 已实现当前历史范围 |
| Webhook Trigger | 已实现当前历史范围 |
| Frontend Governance UI | 已实现当前历史范围 |
| Browser E2E | 已形成独立 Gate |

## 3. 重要边界

历史 Acceptance 的 PASS 只代表当时实际执行的测试结果，不自动证明当前代码不存在新的并发/生产问题。本阶段以当前 `main` 代码重新验证发现的风险。

## 4. 任务拆解

### 1.9-A — Circuit Breaker HALF_OPEN Concurrent Recovery

状态：**本地验证完成，进入 1.9-B。**

目标：

1. HALF_OPEN `half_open_max_calls > 1` 时，成功 Probe 只能释放自己的 Probe reservation。
2. 不能因为一个快速成功 Probe 而在其他 Probe 仍运行时提前 CLOSED。
3. 任一并发 Probe 失败必须重新 OPEN。
4. 继续使用 PostgreSQL 行锁保证跨 worker 的 quota 更新原子性。
5. Policy mismatch 不得消耗新的 Probe reservation。

已完成：

- 修复 `CircuitBreakerService.record_success()` 的 HALF_OPEN reservation 语义。
- 新增并发恢复单元测试覆盖。
- 增加 `half_open_max_calls=2` quota 上限测试。
- 增加 HALF_OPEN policy mismatch 不消耗 quota 的测试。

### 1.9-A 本地实际验证

开发者在最新 `main` 本地实际执行：

```text
Targeted Circuit Breaker tests
→ 16 passed in 0.68s

Alembic
→ PostgreSQL migration upgrade completed successfully

Backend Regression Gate
→ Backend: 262 passed, 20 deselected in 3.64s
→ Migration head: 0022_workflow_trigger (head)
→ Mandatory Real API: 20 passed in 32.99s
→ [PASS] Backend regression gate completed

Standalone Real API Gate
→ 20 passed in 33.26s
→ [PASS] Real API gate completed
```

结论：1.9-A 的代码、专项 Unit Test、Backend Regression、Migration head 和现有 Real API Gate 均已通过当前 main 的本地实际验证。

### 1.9-B — Runtime Failure / Retry / Circuit Boundary Audit

**状态：进行中。**

当前 `WorkflowExecutionService` 已明确：

- `CIRCUIT_OPEN` 不进入 node retry。
- `WORKFLOW_TIMEOUT` 不进入 retry。
- retry 只消耗显式 retryable error code。
- node `max_attempts` 与 workflow `retry_budget.max_retries` 分开约束。
- deadline 在每次 retry 前重新计算，backoff 超过剩余 deadline 时直接以 `WORKFLOW_TIMEOUT` 结束。
- Retry lineage 通过 `retry_of_execution_id` 保留。

当前 `WorkflowRuntime` 已明确：

- transient provider failure 先进入 Circuit Breaker，再由 Workflow Runtime 决定是否 retry。
- HALF_OPEN probe failure 转换为 `CIRCUIT_OPEN`，避免将恢复 Probe 再次消耗 node retry budget。
- Circuit Breaker 与 Workflow retry 使用同一 error classification boundary。

待进一步验证：

- HALF_OPEN probe reservation 当前没有独立 probe token；需要真实超时/并发场景验证迟到旧 Probe completion 不会影响新的 recovery window。
- `record_failure()` / `record_success()` 与 Workflow transition 的事务边界需要真实 PostgreSQL、多 worker 场景验证。

因此 1.9-B 尚不能标记完成。

### 1.9-C — Real API Reliability Scenarios

基于真实数据库和真实 HTTP API 专门验证：

- circuit OPEN fast-fail
- HALF_OPEN recovery
- concurrent probes
- retry lineage
- deadline boundary
- idempotency
- tenant isolation

现有 Backend Gate 的 20 个 Real API 测试已经通过，但不等价于 1.9-C 专项 Reliability Acceptance。

### 1.9-D — Frontend / Browser Reliability Convergence

验证已有 UI/API 的失败态、重复提交、Execution 状态刷新和 Trigger 生命周期，不新增产品范围。

### 1.9-E — Final Acceptance

完成 Backend / Frontend / Browser 三层独立 Gate、Real API、Migration head、关键失败场景和文档同步后关闭 Phase 1.9。

## 5. 验收门禁

必须遵守 `docs/01-governance/DEVELOPMENT.md`：Backend pytest、Alembic upgrade head、Real API Gate、Frontend test/build、Browser E2E、前后端联调。GitHub Actions 不作为本阶段本地验收依据。

## 6. 当前完成定义

1.9-A 已完成本地验证，但 Phase 1.9 整体仍未关闭。

Phase 1.9 只有在 Runtime Reliability 风险完成修复，并通过实际本地 Backend / Real API / Frontend / Browser Gate 后才能标记正式关闭。
