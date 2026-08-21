# Project Status

> 当前项目状态唯一入口。文档治理规则见 `docs/01-governance/DOCUMENTATION.md`，工程开发规则见 `docs/01-governance/DEVELOPMENT.md`。

## 1. 当前基线

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 开发原则：所有任务直接基于最新 `main`，禁止 feature / task / 临时分支。
- 当前文档治理：Docs Governance Refactor 第二阶段已完成。
- 当前开发阶段：**Phase 1.9 — Runtime Reliability / Production Hardening**。

## 2. 整体功能开发进展评估

| 功能域 | 当前状态 | 评估 |
|---|---|---|
| Identity / JWT / RBAC / Tenant | 已实现当前历史范围 | 已形成用户、角色、JWT、Tenant scope 与 Workflow 权限边界；持续作为跨域回归门禁 |
| Agent / AgentVersion / Publish | 已实现当前历史范围 | 已有 Agent/Version、发布版本和 Runtime 使用已发布版本的约束 |
| Agent Chat / Model Gateway | 已实现当前历史范围 | 已形成 Provider Contract、Mock/OpenAI-compatible Provider、普通/流式调用和错误边界；真实 Provider 仍以本地 Real API 为准 |
| Tool Registry / HTTP Tool | 已实现当前历史范围 | 已形成 Registry、AgentTool 权限、Schema、Timeout、响应大小和 SSRF/网络安全边界 |
| Memory | 已实现当前历史范围 | PostgreSQL MemoryRecord/Service 与 Runtime Context 已形成 |
| Observability / Audit / Trace | 已实现当前历史范围 | Execution/Event/Trace/Token/Audit 已形成跨 Runtime / Workflow 关联 |
| Knowledge / Ingestion | 已实现当前历史范围 | Knowledge、Document/Version/Chunk ingestion 和权限边界已形成 |
| Retrieval / Vector / Hybrid | 已实现当前代码范围 | Lexical、Vector、Hybrid、Evaluation 与 Debug 已形成；真实 Embedding Provider 语义质量仍需真实 Provider 评估 |
| Workflow Definition / Version / Execution | **1.9-C 专项验证通过** | Runtime、timeout、retry、deadline、governance 边界已通过当前 focused Unit + Real API Gate；1.9-D 跨层复验通过 |
| Workflow Governance / Audit / Trace | 已实现当前历史范围 | Tenant/RBAC、Audit、Trace、Execution lineage 已形成；本轮 retry audit 已通过 Real API 验证 |
| Retry / Timeout / Idempotency / Deadline | **1.9-C 当前专项验证通过** | retry budget、retry transition、timeout error code、deadline/backoff 与 idempotency reliability 已通过当前 Gate |
| Circuit Breaker | **1.9-C 当前 Real API 验证通过** | Open boundary、retry governance trace 与 fast-fail 场景已通过当前 Gate |
| Scheduled Trigger | **1.9-D 跨层复验通过** | Scheduled Trigger real browser contract 已通过独立 Browser E2E；Final Acceptance 尚未关闭 Phase 1.9 |
| Webhook Trigger | **1.9-D 跨层复验通过** | Webhook browser contract、duplicate convergence 与 lifecycle security 已通过独立 Browser E2E |
| Frontend Governance UI | **1.9-D Frontend Regression 本地复验通过** | AuditLog error-state focused test、Frontend full Vitest、production build、Frontend Regression Gate 均已由开发者本地实际执行通过 |
| Browser E2E | **待本轮前端修复后重新复核** | 此前 3 个 Desktop Chrome tests 已通过；本轮修复后的 Browser E2E 尚未取得新的开发者本地结果 |
| Multi-Agent orchestration | 未纳入当前已完成范围 | 当前架构文档列为长期目标 |
| MQ/Kafka/Event Bus | 未纳入当前范围 | Phase 1.8 明确 Out of Scope |
| 分布式 Worker / Temporal | 未纳入当前范围 | 当前 Runtime 仍为现有单体边界，不宣称已有完整分布式调度系统 |

## 3. Phase 状态

| Phase | 状态 | 说明 |
|---|---|---|
| Phase 1.0 | 已完成 | 基础项目初始化与最小能力 |
| Phase 1.2 | 已完成 | 基础平台、Auth/RBAC、Agent、Session、Runtime、Model/Tool 基础能力 |
| Phase 1.3 | 已完成当前历史范围 | Model Gateway / Tool Runtime / Memory / Observability |
| Phase 1.4 | 已完成当前历史范围 | Knowledge / RAG / Retrieval；真实 Provider 语义质量保持验证边界 |
| Phase 1.5 | 已完成 / 正式关闭 | Workflow / Governance / Reliability / Circuit Breaker 基础能力 |
| Phase 1.6 | 已完成 / 正式关闭 | Trigger / Frontend / Browser 历史范围 |
| Phase 1.7 | 已完成 / 正式关闭 | Scheduled Trigger / Governance / Browser E2E |
| Phase 1.8 | 已完成 / 正式关闭 | Event / Webhook Trigger Expansion |
| **Phase 1.9** | **进行中** | 1.9-A、1.9-B 已验证；1.9-C Runtime Reliability 场景已通过；1.9-D Frontend Regression 已恢复通过，Browser 需本轮修复后复核；1.9-E Final Acceptance 尚未完成 |

## 4. Phase 1.9 当前任务

### 1.9-A Circuit Breaker HALF_OPEN Concurrent Recovery

状态：**本地验证完成。**

历史实际验证：

```text
Targeted Circuit Breaker tests → 16 passed
Backend Regression → 262 passed, 20 deselected
Migration head → 0022_workflow_trigger (head)
Mandatory Real API → 20 passed
Standalone Real API → 20 passed
```

### 1.9-B Runtime Failure / Retry / Circuit Boundary Audit

状态：**focused scope 已完成本地验证。**

已验证：

- `CIRCUIT_OPEN` 不进入 node retry。
- `WORKFLOW_TIMEOUT` 不进入 retry。
- retry 只消耗显式 retryable error code。
- node `max_attempts` 与 workflow `retry_budget.max_retries` 分开约束。
- deadline 在每次 retry 前重新计算，backoff 超过剩余 deadline 时直接以 `WORKFLOW_TIMEOUT` 结束。
- Retry lineage 通过 `retry_of_execution_id` 保留。
- HALF_OPEN stale probe completion 不得修改新的 recovery window。

### 1.9-C Real API Reliability Scenarios

状态：**当前专项验证通过，已进入下一阶段。**

本轮修复后的开发者实际结果：

```text
Focused Runtime / Retry / Timeout suite:
13 passed in 1.17s

Real API Gate:
23 passed in 37.61s
[PASS] Real API gate completed. Frontend/backend integration may proceed.
```

验证覆盖并确认通过：

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

本轮最后一个失败已修复：Real API retry business loop 缺少 `workflow.node.retry` audit。修复提交：

```text
3a0ecfec47ab079b2ce284b56e20a88aa64efd0b
fix: record workflow node retry audit event
```

### 1.9-D Frontend / Browser Reliability Convergence

状态：**Frontend Regression 已由开发者本地复验通过；Browser E2E 待本轮修复后重新复核。**

开发者在最新 `main` 实际执行：

```text
AuditLog focused:
2 passed / 0 failed

Frontend full Vitest:
13 test files passed
52 tests passed

Frontend production build:
passed

Frontend Regression Gate:
[PASS] Frontend regression gate completed. Backend remains an independent gate.
```

测试输出中的：

```text
AuditLog query failed TypeError: Cannot read properties of undefined (reading 'data')
```

来自 malformed response fixture 进入组件既有 `catch` 路径时的 `console.error`，并未造成测试失败或 Gate 阻塞。

根因与修复：

- `AuditLogPanel.vue` 生产代码已经在 `load()` 的 `try/catch` 中处理 Audit API 异常。
- 原 error-state fixture 使用 rejected Promise，与 Vitest 当前 unhandled-rejection 调度产生时序耦合。
- 最终测试边界改为 `mockResolvedValue(undefined)`，利用 malformed envelope 稳定进入组件 `catch/finally` 路径，不依赖 rejected Promise 的调度时序。
- 生产 `AuditLogPanel.vue` 无需无关修改。
- 工程错误已记录并关闭：`docs/04-errors/ERR-0020-frontend-audit-log-error-state-mock-rejection.md`。

### 1.9-E Final Acceptance

状态：**待执行。**

Frontend Regression 已恢复后，下一步必须完成：

1. Browser E2E 本轮修复后的独立复核；
2. Backend default regression；
3. Alembic `upgrade head` / migration head；
4. Real API Gate；
5. 关键失败场景复核；
6. Backend / Frontend / Browser 三层 Gate 文档同步；
7. 全部通过后才可关闭 Phase 1.9。

## 5. 已完成文档治理整改

Docs Governance Refactor 第二阶段已经完成：

```text
docs/
├── README.md
├── PROJECT_STATUS.md
├── DOCS_MIGRATION_MATRIX.md
├── 00-architecture/
├── 01-governance/
├── 02-phases/
├── 03-acceptance/
└── 04-errors/
```

## 6. 当前 Phase 1.9 实际测试记录

```text
1.9-A Circuit Breaker targeted tests: 16 passed
1.9-A Backend Regression: 262 passed, 20 deselected
1.9-A Alembic head: 0022_workflow_trigger
1.9-A Real API via Backend Gate: 20 passed
1.9-A Standalone Real API Gate: 20 passed

1.9-B Focused runtime tests: 35 passed
1.9-B Backend Regression: 264 passed, 20 deselected
1.9-B Alembic head: 0022_workflow_trigger
1.9-B Real API via Backend Gate: 20 passed
1.9-B Standalone Real API Gate: 20 passed

1.9-C Previous failing Real API Gate: 22 passed, 1 failed
Fixed: workflow.node.retry audit missing

1.9-C Latest focused Runtime / Retry / Timeout suite: 13 passed in 1.17s
1.9-C Latest Real API Gate: 23 passed in 37.61s

1.9-D Previous Frontend Vitest: 13 test files passed, 52 tests passed
1.9-D Previous Frontend production build: passed
1.9-D Previous Frontend Regression Gate: passed
1.9-D Previous Browser E2E: 3 passed in 12.0s

1.9-D Latest developer feedback:
AuditLog focused: 2 passed
Frontend Vitest: 13 test files / 52 tests passed
Frontend production build: passed
Frontend Regression Gate: passed
Browser E2E: pending re-run after the final AuditLog test fix
```

## 7. 当前风险 / 未完成范围

1. 1.9-A 与 1.9-B 已通过各自历史本地验证。
2. 1.9-C 当前 Runtime / Retry / Timeout focused suite 与 Real API Gate 已通过最新开发者本地执行结果。
3. 1.9-D Frontend Regression 已恢复通过；Browser E2E 尚未取得本轮修复后的重新验证结果。
4. Cross-Tenant isolation 尚未形成真实 API 测试上下文。
5. 1.9-E Final Acceptance 尚未执行，因此不能关闭 Phase 1.9。
6. Multi-Agent orchestration、MQ/Kafka/Event Bus、Temporal/完整分布式 Worker 不属于当前已完成范围。

## 8. 下一步执行顺序

严格遵守 `docs/01-governance/DEVELOPMENT.md`：

1. **Frontend Regression 已恢复，下一步先执行本轮修复后的 Browser E2E，不能直接沿用此前 3 个通过结果。**
2. **Browser E2E 通过后进入 1.9-E Final Acceptance：重新执行 Backend default regression、Alembic migration/head、Real API Gate。**
3. **同步复核关键失败场景与三层 Gate 独立性。**
4. 发现新的工程错误立即记录到 `docs/04-errors/`，不提前关闭当前错误。
5. 完成 1.9-E 后执行 Final Acceptance，并同步对应 Phase / Acceptance 文档。
6. 最终通过 Backend / Frontend / Browser 三层独立 Gate 后关闭 Phase 1.9。
