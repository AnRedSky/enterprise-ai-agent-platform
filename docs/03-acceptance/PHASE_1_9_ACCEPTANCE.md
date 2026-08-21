# Phase 1.9 Acceptance — Runtime Reliability / Production Hardening

> 状态：进行中
> 基线：最新 `main`

## 1. Acceptance 原则

本文件只记录开发者本地实际执行的验收结果，不预填 PASS，不使用 GitHub Actions 替代本地验收。

## 2. 1.9-A Acceptance

### Circuit Breaker HALF_OPEN Concurrent Recovery

| Gate | 实际结果 | 状态 |
|---|---:|---|
| Circuit Breaker targeted tests | 16 passed / 0.68s | PASS |
| Alembic upgrade head | PostgreSQL upgrade completed | PASS |
| Migration head | `0022_workflow_trigger` | PASS |
| Backend Regression | 262 passed, 20 deselected / 3.64s | PASS |
| Mandatory Real API | 20 passed / 32.99s | PASS |
| Standalone Real API | 20 passed / 33.26s | PASS |

结论：**1.9-A 已通过本地实际验证。**

## 3. 1.9-B Acceptance

### 当前实现

已完成 Runtime Failure / Retry / Circuit Boundary 的 stale Probe completion 修复：

- HALF_OPEN Probe reservation 继续受 PostgreSQL 行锁保护。
- Probe completion 绑定当前 Recovery Window。
- 使用现有 `half_opened_at` 作为 Recovery Window generation boundary。
- stale Probe success 不得关闭新的 Recovery Window。
- stale Probe failure 不得重新 OPEN 新的 Recovery Window。
- 未经过 `before_call()` 的直接 service-level success/failure 调用保持兼容。

对应代码提交：

```text
8085e5c7c6009a97a7d3a1d73094f7812c9f9258
fix: isolate stale circuit probe completions
```

对应专项测试提交：

```text
f7ef0c55810171cb70e5873a99cba82a01a64047
test: cover stale half-open probe completion
```

### 本地实际验证

开发者在最新 `main` 实际执行：

| Gate | 实际结果 | 状态 |
|---|---:|---|
| Focused 1.9-B runtime tests | 35 passed / 0.97s | PASS |
| Backend Regression | 264 passed, 20 deselected / 4.79s | PASS |
| Alembic upgrade/head | `0022_workflow_trigger` | PASS |
| Mandatory Real API | 20 passed / 40.74s | PASS |
| Standalone Real API | 20 passed / 31.38s | PASS |

结论：**1.9-B 当前 focused scope 已通过本地 Backend / PostgreSQL / Real API 验证。**

## 4. 1.9-C Acceptance — Real API Reliability Scenarios

状态：**当前专项验证通过。**

### 覆盖范围

- Workflow node timeout 与 workflow deadline timeout 的 HTTP 504 语义。
- `NODE_TIMEOUT` / `WORKFLOW_TIMEOUT` error code 持久化边界。
- node retry transition 与 retry attempt lineage。
- workflow retry budget exhaustion。
- retry backoff crossing workflow deadline。
- retry policy / retryable error code boundary。
- Real API node retry business loop。
- retry governance trace：`node.retry.scheduled`。
- retry governance audit：`workflow.node.retry`、`workflow.node.retry_exhausted`、`workflow.execution.failed`。
- Circuit Breaker open / fast-fail boundary。
- Real HTTP idempotency reliability 场景。

### 修复与最终本地结果

首轮 Real API Gate 曾出现：

```text
22 passed, 1 failed
```

失败根因包括 Workflow Runtime orchestration 缺失以及 idempotency race transaction recovery 问题，均已修复。

随后开发者在最新 `main` 实际执行：

```text
Focused Runtime / Retry / Timeout suite:
13 passed in 1.17s

Real API Gate:
23 passed in 37.61s
[PASS] Real API gate completed. Frontend/backend integration may proceed.
```

本轮最后一个失败为 Real API retry business loop 缺少 `workflow.node.retry` audit，修复提交：

```text
3a0ecfec47ab079b2ce284b56e20a88aa64efd0b
fix: record workflow node retry audit event
```

本轮 Real API 场景现已通过，因此 1.9-C 不再处于 bootstrap blocking 状态。

当前注册接口仍将新用户绑定到 canonical `DEFAULT_TENANT_ID`，因此 ownership isolation 不等价于跨 Tenant isolation；Cross-Tenant isolation 仍不属于本阶段已完成的真实 API 验收范围。

## 5. 1.9-D Acceptance — Frontend / Browser Reliability Convergence

状态：**本轮 Frontend / Browser Gate 均已实际通过。**

### Frontend 本地实际结果

开发者在最新 `main` 实际执行：

```text
Frontend full Vitest:
13 test files passed
52 tests passed

Frontend production build:
passed

Frontend Regression Gate:
[PASS] Frontend regression gate completed. Backend remains an independent gate.
```

AuditLog focused regression 同时为：

```text
2 passed / 0 failed
```

测试输出中的：

```text
AuditLog query failed TypeError: Cannot read properties of undefined (reading 'data')
```

来自 malformed response fixture 进入组件既有 `catch` 路径时的 `console.error`，没有造成测试失败，也没有阻塞 Frontend Regression Gate。

对应工程错误已关闭并重新编号为：

```text
docs/04-errors/ERR-0020-frontend-audit-log-error-state-mock-rejection.md
```

### Browser E2E 本轮实际结果

开发者在最新 `main` 实际执行 Desktop Chrome Browser Gate：

```text
3 tests passed in 10.5s

1. Scheduled Trigger real browser contract: PASS
2. Webhook Trigger real browser contract: PASS
3. Webhook duplicate-event convergence and lifecycle security: PASS

[PASS] Phase 1.7-D browser E2E gate completed.
```

因此本轮 1.9-D 的 Browser Gate 已取得新的本地实际通过证据，不再沿用 AuditLog 修复前的历史结果。

## 6. 1.9-E Final Acceptance

状态：**进行中，等待本轮 Migration / head 实际复核后关闭。**

### 本轮已取得的独立 Gate 结果

| Gate | 实际结果 | 状态 |
|---|---:|---|
| Browser E2E | 3 passed / 10.5s | PASS |
| Frontend Vitest | 13 files / 52 tests passed | PASS |
| Frontend production build | passed | PASS |
| Frontend Regression Gate | PASS | PASS |
| Backend default regression | 264 passed, 23 deselected / 4.80s | PASS |
| Real API Gate | 23 passed / 39.47s | PASS |

### Migration / head

本轮 Final Acceptance 还需要开发者实际执行并记录：

```powershell
cd backend
uv run alembic upgrade head
uv run alembic current
uv run alembic heads
```

预期 head：

```text
0022_workflow_trigger (head)
```

本轮未收到上述三条命令的完整新输出，因此这里不提前标记 Migration PASS，也不关闭 Phase 1.9。

### 关键失败场景复核

本轮 Backend Regression 与 Real API Gate 已重新通过，覆盖 1.9-C 的 Runtime / Retry / Timeout / Idempotency / Circuit Breaker reliability 范围；Browser E2E 同时重新验证 Scheduled Trigger、Webhook Trigger、duplicate convergence 与 lifecycle security。

## 7. Phase 1.9 关闭条件

必须同时满足：

- 1.9-A Acceptance PASS；
- 1.9-B Runtime Failure / Retry / Circuit Boundary PASS；
- 1.9-C Real API Reliability PASS；
- 1.9-D Frontend / Browser Reliability PASS；
- Backend / Frontend / Browser 独立 Gate 均来自本地实际执行；
- Migration head 正确并有本轮实际命令输出；
- PROJECT_STATUS 与 Phase / Acceptance 文档同步；
- 无未记录的阻塞错误。

当前只剩 **Migration / head 的本轮实际复核及最终文档同步**，因此暂不关闭 Phase 1.9。
