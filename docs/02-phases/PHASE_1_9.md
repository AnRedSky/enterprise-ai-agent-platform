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
| Retry / Timeout / Idempotency / Deadline | 已实现当前历史范围 |
| Circuit Breaker | 已实现基础状态机；当前发现 HALF_OPEN 并发恢复一致性缺口 |
| Scheduled Trigger | 已实现当前历史范围 |
| Webhook Trigger | 已实现当前历史范围 |
| Frontend Governance UI | 已实现当前历史范围 |
| Browser E2E | 已形成独立 Gate |

## 3. 重要边界

历史 Acceptance 的 PASS 只代表当时实际执行的测试结果，不自动证明当前代码不存在新的并发/生产问题。本阶段以当前 `main` 代码重新验证发现的风险。

## 4. 任务拆解

### 1.9-A — Circuit Breaker HALF_OPEN Concurrent Recovery

状态：实现中，待本地 Gate。

目标：

1. HALF_OPEN `half_open_max_calls > 1` 时，成功 Probe 只能释放自己的 Probe reservation。
2. 不能因为一个快速成功 Probe 而在其他 Probe 仍运行时提前 CLOSED。
3. 任一并发 Probe 失败必须重新 OPEN。
4. 继续使用 PostgreSQL 行锁保证跨 worker 的 quota 更新原子性。

已完成：

- 修复 `CircuitBreakerService.record_success()` 的 HALF_OPEN reservation 语义。
- 新增并发恢复单元测试覆盖。

待验证：

```powershell
cd backend
uv run pytest -q backend/tests/unit/test_circuit_breaker.py backend/tests/unit/test_circuit_breaker_half_open_concurrency.py
```

以及完整 Backend Gate、Alembic head、Real API Gate。

### 1.9-B — Runtime Failure / Retry / Circuit Boundary Audit

检查 Retry、Deadline、Circuit Open、Provider failure、Workflow terminal state 之间是否存在重复重试、错误码包装或 budget 泄漏。

### 1.9-C — Real API Reliability Scenarios

基于真实数据库和真实 HTTP API 验证 circuit OPEN fast-fail、HALF_OPEN recovery、concurrent probes、retry lineage、deadline boundary、idempotency、tenant isolation。

### 1.9-D — Frontend / Browser Reliability Convergence

验证已有 UI/API 的失败态、重复提交、Execution 状态刷新和 Trigger 生命周期，不新增产品范围。

### 1.9-E — Final Acceptance

完成 Backend / Frontend / Browser 三层独立 Gate、Real API、Migration head、关键失败场景和文档同步后关闭 Phase 1.9。

## 5. 验收门禁

必须遵守 `docs/01-governance/DEVELOPMENT.md`：Backend pytest、Alembic upgrade head、Real API Gate、Frontend test/build、Browser E2E、前后端联调。GitHub Actions 不作为本阶段本地验收依据。

## 6. 完成定义

Phase 1.9 只有在 Runtime Reliability 风险完成修复，并通过实际本地 Backend / Real API / Frontend / Browser Gate 后才能标记正式关闭。
