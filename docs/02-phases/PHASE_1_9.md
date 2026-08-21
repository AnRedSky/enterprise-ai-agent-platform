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

**状态：当前专项修复已通过本地验证。**

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

### 1.9-C — Real API Reliability Scenarios

**状态：专项修复已直接提交最新 `main`，等待开发者本地重新验证；当前不能标记 PASS。**

新增专项测试文件：

```text
backend/tests/api_real/test_phase_1_9c_reliability_api.py
```

新增场景：

- Workflow Execution `Idempotency-Key` 顺序重放必须返回同一 Execution。
- 两个并发真实 HTTP 请求使用相同 `Idempotency-Key` 时必须收敛到同一个 Execution，不能产生重复 Execution 或 500。
- 同一 Tenant 下另一用户不能读取其他用户创建的 Execution，验证当前 Execution ownership isolation boundary。

当前注册接口将新用户绑定到 canonical `DEFAULT_TENANT_ID`，因此第三项是**同 Tenant ownership isolation**，不能扩大解释为跨 Tenant isolation。跨 Tenant 专项仍待能够创建不同 Tenant 的真实 API 测试上下文后执行。

#### 已有首轮失败证据

直接运行专项测试时，三个测试因没有提前准备 `WORKFLOW_ID` context 而失败：

```text
3 failed in 0.10s
WORKFLOW_ID is required for 1.9-C reliability validation
```

随后通过正式 Real API Gate 自动 bootstrap context 后执行完整 suite：

```text
22 passed, 1 failed in 39.35s
```

唯一失败：

```text
test_execution_idempotency_is_race_safe_over_real_http
```

实际一个并发请求返回 HTTP 500；测试随后解析纯文本 `Internal Server Error` 时产生 `JSONDecodeError`，已修正诊断逻辑以保留原始 HTTP body。

#### 已修复的 Idempotency 并发边界

Idempotency 创建路径已使用 `AsyncSession.begin_nested()` SAVEPOINT，并在竞争异常后使用保存的标量 ID 重新查询已经提交的 Execution，避免完整 rollback 后访问过期 ORM 对象造成异步隐式加载风险。

错误记录：

```text
docs/04-errors/ERR-0018-idempotency-race-missinggreenlet.md
```

#### 本轮新增发现：Runtime Retry / Timeout Failure Semantics

在继续验证 1.9-C 前置 Runtime boundary 时，开发者本地实际反馈：

```text
7 failed, 6 passed, 1 warning
```

失败集中在 workflow timeout、retry budget、retry transition 与 retry deadline；错误表现为原始 `HTTPException(503)` / `ConnectionError` / `TimeoutError` 被最终包装为 `HTTP 500 Workflow Runtime 执行失败`。

Real API bootstrap 同时出现 retry deadline fixture 预期 `HTTP 504`、实际 `HTTP 404 Mock provider HTTP 404` 的边界失败。

错误记录：

```text
docs/04-errors/ERR-0019-workflow-runtime-retry-failure-semantics.md
```

当前修复已提交到 `main`：

- `WorkflowRuntime` 保存节点失败原始异常，在 retry policy / node attempts / retry budget 耗尽时保留 HTTP、transport、timeout 的类型语义。
- `WorkflowExecutionService.run()` 对 `ConnectionError` / timeout 单独记录 failed/error_code 后重新抛出，不再统一包装为 500。
- retry backoff 在 sleep 前重新计算 workflow remaining deadline，超过剩余 deadline 时直接返回 504 `WORKFLOW_TIMEOUT`。
- 该修复不新增数据库结构，因此不产生 migration 变更。

相关代码提交：

```text
c26db148d6a97b1a2ce908b39b6b00d517da8a4b
fix: preserve workflow retry failure semantics

bb0bcd9e91566bd47c5c2ebbaa5c7be216378971
fix: preserve typed workflow runtime failures
```

**注意：上述修复尚未获得新的本地 PASS 证据，因此 1.9-C 仍不能标记 PASS。**

下一步必须重新执行 Runtime focused tests 与完整 Real API Gate；通过后再继续跨 Tenant / stale completion 等专项场景。

### 1.9-D — Frontend / Browser Reliability Convergence

验证已有 UI/API 的失败态、重复提交、Execution 状态刷新和 Trigger 生命周期，不新增产品范围。

### 1.9-E — Final Acceptance

完成 Backend / Frontend / Browser 三层独立 Gate、Real API、Migration head、关键失败场景和文档同步后关闭 Phase 1.9。

## 5. 验收门禁

必须遵守 `docs/01-governance/DEVELOPMENT.md`：Backend pytest、Alembic upgrade head、Real API Gate、Frontend test/build、Browser E2E、前后端联调。GitHub Actions 不作为本阶段本地验收依据。

## 6. 当前完成定义

1.9-A 已完成本地验证；1.9-B focused scope 已完成本地验证；1.9-C 已发现并修复 Idempotency 并发与 Runtime retry/timeout failure semantics 问题，但当前修复等待开发者本地重新验证。

Phase 1.9 只有在 1.9-C、1.9-D、1.9-E 完成并通过实际本地 Backend / Real API / Frontend / Browser Gate 后才能标记正式关闭。
