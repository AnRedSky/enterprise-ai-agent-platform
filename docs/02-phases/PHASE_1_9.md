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
| Circuit Breaker | 1.9-A 已通过本地 Gate；1.9-B stale Probe completion 已通过本地验证 |
| Scheduled Trigger | 已实现当前历史范围 |
| Webhook Trigger | 已实现当前历史范围 |
| Frontend Governance UI | 已实现当前历史范围 |
| Browser E2E | 已形成独立 Gate |

## 3. 重要边界

历史 Acceptance 的 PASS 只代表当时实际执行的测试结果，不自动证明当前代码不存在新的并发/生产问题。本阶段以当前 `main` 代码重新验证发现的风险。

## 4. 任务拆解

### 1.9-A — Circuit Breaker HALF_OPEN Concurrent Recovery

状态：**本地验证完成。**

本地实际验证：

```text
Targeted Circuit Breaker tests → 16 passed in 0.68s
Backend Regression → 262 passed, 20 deselected in 3.64s
Migration head → 0022_workflow_trigger (head)
Mandatory Real API → 20 passed in 32.99s
Standalone Real API → 20 passed in 33.26s
```

### 1.9-B — Runtime Failure / Retry / Circuit Boundary Audit

**状态：当前专项修复已通过本地验证，继续进入 1.9-C。**

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

本轮已发现并修复的边界：

> 旧 Recovery Window 的迟到 Probe completion 不能修改新的 HALF_OPEN Recovery Window。

实现方式：

- 在 Circuit Breaker 的 async execution context 中记录 `(tenant_id, circuit_key, half_opened_at)` Probe reservation token。
- `record_success()` / `record_failure()` 在 HALF_OPEN 状态下校验 token 对应的 recovery window。
- stale completion 与当前 window 不匹配时只释放当前调用上下文，不修改新 window 的 state/quota。
- 直接调用 `record_success()` / `record_failure()` 且没有 Probe token 的历史 service-level 调用仍保持兼容。
- 本修复不新增数据库字段或 migration；Recovery Window 复用现有 `half_opened_at` 作为 generation boundary。

代码提交：

```text
8085e5c7c6009a97a7d3a1d73094f7812c9f9258
fix: isolate stale circuit probe completions
```

新增专项测试覆盖：

- stale HALF_OPEN success 不关闭新的 recovery window。
- stale HALF_OPEN failure 不重新 OPEN 新的 recovery window。

测试提交：

```text
f7ef0c55810171cb70e5873a99cba82a01a64047
 test: cover stale half-open probe completion
```

### 1.9-B 本地真实验证结果

开发者在最新 `main` 本地实际执行：

```text
Focused 1.9-B runtime tests → 35 passed in 0.97s
Backend Regression → 264 passed, 20 deselected in 4.79s
Migration head → 0022_workflow_trigger (head)
Mandatory Real API → 20 passed in 40.74s
Standalone Real API → 20 passed in 31.38s
```

因此 **1.9-B 当前 focused scope 已通过本地 Backend / PostgreSQL / Real API 验证。**

### 1.9-B 完成边界

本次 Acceptance 覆盖 stale Probe completion、Circuit Breaker 与 Retry/Timeout/Deadline 现有边界测试。当前没有发现需要继续修改代码的 1.9-B blocking issue。

后续可靠性专项进入 1.9-C；如 Real API 场景发现新的跨 worker、retry、idempotency 或 tenant isolation 问题，应新增错误记录并回到相应修复任务。

### 1.9-C — Real API Reliability Scenarios

基于真实数据库和真实 HTTP API 专门验证：

- circuit OPEN fast-fail
- HALF_OPEN recovery
- concurrent probes
- stale Probe completion
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

1.9-A 已完成本地验证；1.9-B focused scope 已完成本地验证。

Phase 1.9 只有在 1.9-C、1.9-D、1.9-E 完成并通过实际本地 Backend / Real API / Frontend / Browser Gate 后才能标记正式关闭。
