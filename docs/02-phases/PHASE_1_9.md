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
| Workflow / Execution / Governance | 1.9-C Runtime reliability 专项已通过当前本地验证 |
| Retry / Timeout / Idempotency / Deadline | 1.9-C 当前 focused + Real API 验证通过 |
| Circuit Breaker | 1.9-A/1.9-B 已验证，1.9-C Real API boundary 已通过 |
| Scheduled Trigger | 已实现当前历史范围；1.9-D 跨层复验通过 |
| Webhook Trigger | 已实现当前历史范围；1.9-D Browser E2E 复验通过 |
| Frontend Governance UI | 已实现当前历史范围；1.9-D Frontend regression/build 通过 |
| Browser E2E | 独立 Gate 已通过当前 1.9-D 范围 |

## 3. 重要边界

历史 Acceptance 的 PASS 只代表当时实际执行的测试结果，不自动证明当前代码不存在新的并发/生产问题。本阶段以当前 `main` 代码重新验证发现的风险。

## 4. 任务拆解

### 1.9-A — Circuit Breaker HALF_OPEN Concurrent Recovery

状态：**本地验证完成。**

历史实际验证：

```text
Targeted Circuit Breaker tests → 16 passed
Backend Regression → 262 passed, 20 deselected
Migration head → 0022_workflow_trigger (head)
Mandatory Real API → 20 passed
Standalone Real API → 20 passed
```

### 1.9-B — Runtime Failure / Retry / Circuit Boundary Audit

状态：**focused scope 已完成本地验证。**

已验证：

- `CIRCUIT_OPEN` 不进入 node retry。
- `WORKFLOW_TIMEOUT` 不进入 retry。
- retry 只消耗显式 retryable error code。
- node `max_attempts` 与 workflow `retry_budget.max_retries` 分开约束。
- deadline 在每次 retry 前重新计算，backoff 超过剩余 deadline 时直接以 `WORKFLOW_TIMEOUT` 结束。
- Retry lineage 通过 `retry_of_execution_id` 保留。
- HALF_OPEN stale probe completion 不得修改新的 recovery window。

### 1.9-C — Real API Reliability Scenarios

状态：**当前专项验证通过。**

本轮开发者本地实际执行：

```text
Focused Runtime / Retry / Timeout suite:
13 passed in 1.17s

Real API Gate:
23 passed in 37.61s
[PASS] Real API gate completed. Frontend/backend integration may proceed.
```

已通过的边界包括：

- Workflow node timeout / workflow deadline timeout → HTTP 504。
- `NODE_TIMEOUT` / `WORKFLOW_TIMEOUT` error code preservation。
- node retry transition 与 attempt lineage。
- workflow retry budget exhaustion。
- retry backoff crossing workflow deadline。
- retry policy / retryable error code boundary。
- Real API node retry business loop。
- `node.retry.scheduled` trace。
- `workflow.node.retry`、`workflow.node.retry_exhausted`、`workflow.execution.failed` audit。
- Circuit Breaker open / fast-fail boundary。
- Real HTTP idempotency reliability 场景。

本轮最后一个失败为 Real API retry business loop 缺少 `workflow.node.retry` audit。已修复并提交：

```text
3a0ecfec47ab079b2ce284b56e20a88aa64efd0b
fix: record workflow node retry audit event
```

修复位于 `WorkflowRuntime` retry scheduling 路径：确认 retry 不因 node policy、workflow budget 或 deadline exhaustion 被截断后，在 backoff sleep 前记录 `workflow.node.retry` audit，并携带 node、next attempt、delay metadata。

因此 1.9-C 不再存在当前已知的 Runtime retry / timeout / governance Real API failure；后续不得重复修改已通过的边界，除非新的 Gate 暴露回归。

### 1.9-D — Frontend / Browser Reliability Convergence

状态：**当前开发者本地验证通过。**

本轮实际执行结果：

```text
Frontend Vitest:
13 test files passed
52 tests passed

Frontend production build:
passed

Frontend Regression Gate:
[PASS] Frontend regression gate completed.

Browser E2E:
3 passed in 12.0s
[PASS] Phase 1.7-D browser E2E gate completed.
```

Browser Gate 实际覆盖：

- Scheduled Trigger real browser contract。
- Webhook Trigger real browser contract。
- Webhook duplicate-event convergence 与 lifecycle security。
- Browser → Vue UI → Backend HTTP → Workflow Trigger Governance 跨层链路。

另外，Frontend `AuditLogPanel` 的 error-state 测试 fixture 已从“返回不完整响应对象”修正为真实 API rejection 场景，避免测试通过时产生无意义的 `TypeError` stderr；生产代码无需因此改变。

因此 1.9-D 当前定义范围的 Frontend / Browser Gate 已通过。尚未因此提前关闭 Phase 1.9，1.9-E Final Acceptance 仍需独立执行。

### 1.9-E — Final Acceptance

状态：**下一项任务。**

完成 Backend / Frontend / Browser 三层独立 Gate、Real API、Migration head、关键失败场景和文档同步后关闭 Phase 1.9。

## 5. 验收门禁

必须遵守 `docs/01-governance/DEVELOPMENT.md`：Backend pytest、Alembic upgrade head、Real API Gate、Frontend test/build、Browser E2E、前后端联调。GitHub Actions 不作为本阶段本地验收依据。

Backend、Frontend、Browser 三层 Gate 必须独立执行，不创建 Full Regression Gate。

## 6. 当前完成定义

1.9-A 已完成本地验证；1.9-B focused scope 已完成本地验证；**1.9-C 已通过当前开发者本地 focused Runtime / Retry / Timeout suite 与完整 Real API Gate；1.9-D Frontend / Browser Reliability Convergence 已通过当前开发者本地 Frontend Regression Gate 与独立 Browser E2E Gate。**

Phase 1.9 只有在 1.9-E 完成并通过实际本地 Backend / Real API / Frontend / Browser Gate 后才能标记正式关闭。

## 7. 下一步

1. 进入 1.9-E Final Acceptance。
2. 重新执行 Backend default regression、Alembic migration head 与 Real API Gate，确认 1.9-C 后端基线没有回归。
3. 复核 Frontend Regression Gate 与 Browser E2E Gate 的当前结果。
4. 完成关键失败场景、跨层联调与文档一致性检查。
5. 发现新错误立即记录 `docs/04-errors/`，不提前关闭 Phase 1.9。
6. 通过 1.9-E 后同步 `PROJECT_STATUS.md` 与 Acceptance 文档，并正式关闭 Phase 1.9。
