# Project Status

> 当前项目状态唯一入口。文档治理规则见 `docs/01-governance/DOCUMENTATION.md`，工程开发规则见 `docs/01-governance/DEVELOPMENT.md`。

## 1. 当前基线

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 开发原则：所有任务直接基于最新 `main`，禁止 feature / task / 临时分支。
- 当前文档治理：Docs Governance Refactor 第二阶段已完成。
- 当前开发阶段：**Phase 1.9 — Runtime Reliability / Production Hardening**。

## 2. 整体功能开发进展评估

> 本节是当前产品能力的开发状态评估，不把历史 Phase Acceptance 的 PASS 扩大解释为“当前所有生产能力均已完成”。“已实现当前历史范围”表示已有代码、Contract 和历史验收证据；“待生产化”表示仍需要当前 main 上的真实场景、并发、失败恢复或跨层 Gate 重新验证。

| 功能域 | 当前状态 | 评估 |
|---|---|---|
| Identity / JWT / RBAC / Tenant | 已实现当前历史范围 | 已形成用户、角色、JWT、Tenant scope 与 Workflow 权限边界；仍需持续作为跨域回归门禁 |
| Agent / AgentVersion / Publish | 已实现当前历史范围 | 已有 Agent/Version、发布版本和 Runtime 使用已发布版本的约束 |
| Agent Chat / Model Gateway | 已实现当前历史范围 | 已形成 Provider Contract、Mock/OpenAI-compatible Provider、普通/流式调用和错误边界；真实 Provider 仍以本地 Real API 为准 |
| Tool Registry / HTTP Tool | 已实现当前历史范围 | 已形成 Registry、AgentTool 权限、Schema、Timeout、响应大小和 SSRF/网络安全边界 |
| Memory | 已实现当前历史范围 | PostgreSQL MemoryRecord/Service 与 Runtime Context 已形成；当前不扩展向量记忆/自动摘要等未纳入范围的能力 |
| Observability / Audit / Trace | 已实现当前历史范围 | Execution/Event/Trace/Token/Audit 已形成跨 Runtime / Workflow 关联 |
| Knowledge / Ingestion | 已实现当前历史范围 | Knowledge、Document/Version/Chunk ingestion 和权限边界已形成 |
| Retrieval / Vector / Hybrid | 已实现当前代码范围 | Lexical、Vector、Hybrid、Evaluation 与 Debug 已形成；真实 Embedding Provider 的语义质量不能由 Mock 结论替代 |
| Workflow Definition / Version / Execution | 已实现当前历史范围 | Definition、Publish、Execution State Machine、Runtime Integration 已形成 |
| Workflow Governance / Audit / Trace | 已实现当前历史范围 | Tenant/RBAC、Audit、Trace、Execution lineage 已形成 |
| Retry / Timeout / Idempotency / Deadline | 已实现当前历史范围 | 基础 Contract 已形成；Phase 1.9-B 正在重新验证 Retry / Deadline / Circuit 跨边界行为 |
| Circuit Breaker | **正在修复 / 验证** | 1.9-A 已完成代码修复；专项测试、完整 Backend Gate、Migration head、Real API Gate 均已由开发者本地实际执行并通过；仍需完成 1.9-B/C/D 才能完成 Phase 1.9 Reliability Acceptance |
| Scheduled Trigger | 已实现当前历史范围 | Phase 1.7 已形成持久化、治理和 Browser E2E 能力 |
| Webhook Trigger | 已实现当前历史范围 | Phase 1.8 已形成认证、durable idempotency、Workflow Execution 和 Browser E2E |
| Frontend Governance UI | 已实现当前历史范围 | Vue 管理端已覆盖 Agent/Workflow/Knowledge/Trigger 等历史范围 |
| Browser E2E | 已形成独立 Gate | 已有 Playwright 场景；当前继续作为跨层可靠性验证层 |
| Multi-Agent orchestration | **未纳入当前已完成范围** | 当前架构文档列为长期目标，不应宣称已经完成 |
| MQ/Kafka/Event Bus | **未纳入当前范围** | Phase 1.8 明确 Out of Scope |
| 分布式 Worker / Temporal | **未纳入当前范围** | 当前 Runtime 仍为现有单体边界，不宣称已有完整分布式调度系统 |

## 3. Phase 状态

| Phase | 状态 | 说明 |
|---|---|---|
| Phase 1.0 | 已完成 | 基础项目初始化与最小能力 |
| Phase 1.2 | 已完成 | 基础平台、Auth/RBAC、Agent、Session、Runtime、Model/Tool 基础能力 |
| Phase 1.3 | 已完成当前历史范围 | Model Gateway / Tool Runtime / Memory / Observability |
| Phase 1.4 | 已完成当前历史范围 | Knowledge / RAG / Retrieval；真实 Provider 语义质量保持验证边界 |
| Phase 1.5 | 已完成 / 正式关闭 | Workflow / Governance / Reliability / Circuit Breaker 基础能力 |
| Phase 1.6 | 已完成 / 正式关闭 | Trigger / Frontend / Browser 历史范围；未发现独立 1.6-D 正文，不补造 |
| Phase 1.7 | 已完成 / 正式关闭 | Scheduled Trigger / Governance / Browser E2E |
| Phase 1.8 | 已完成 / 正式关闭 | Event / Webhook Trigger Expansion |
| **Phase 1.9** | **进行中** | 1.9-A 本地验证完成；1.9-B Runtime Failure / Retry / Circuit Boundary Audit 继续进行 |

## 4. Phase 1.9 当前任务

### 1.9-A Circuit Breaker HALF_OPEN Concurrent Recovery

状态：**本地验证完成，待进入 1.9-B。**

开发者实际执行结果：

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

因此 1.9-A 的代码、专项 Unit Test、Backend Regression、Migration head 和 Real API Gate 均已获得当前 main 的本地实际验证证据。

### 1.9-B Runtime Failure / Retry / Circuit Boundary Audit

状态：**进行中。**

当前代码已确认：

- `CIRCUIT_OPEN` 不进入 node retry。
- `WORKFLOW_TIMEOUT` 不进入 retry。
- retry 只消耗显式 retryable error code。
- node `max_attempts` 与 workflow `retry_budget.max_retries` 分开约束。
- retry backoff 超过 workflow 剩余 deadline 时以 `WORKFLOW_TIMEOUT` 结束。
- retry lineage 通过 `retry_of_execution_id` 保留。
- HALF_OPEN probe failure 会转换为 `CIRCUIT_OPEN`，避免恢复 Probe 再次消耗 node retry budget。

仍需继续验证：

- HALF_OPEN reservation 当前没有独立 probe token；需要真实超时/并发场景验证迟到旧 Probe completion 不会影响新的 recovery window。
- `record_failure()` / `record_success()` 与 Workflow transition 的事务边界需要真实 PostgreSQL、多 worker 场景验证。
- 1.9-C 需要扩展 Real API Reliability Scenarios，覆盖 OPEN fast-fail、HALF_OPEN recovery、concurrent probes、retry lineage、deadline boundary、idempotency、tenant isolation。

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

Phase 1.4、1.5、1.6、1.7、历史 Phase 14–24 以及旧 `error-tracking` 已逐份核对、迁移并清理旧入口。不存在独立历史正文的任务没有被补造。

## 6. 当前 Phase 1.9 实际测试记录

本轮实际结果全部来自开发者本地反馈，不使用 GitHub Actions 作为验收依据：

```text
Circuit Breaker targeted tests: 16 passed in 0.68s
Backend Regression: 262 passed, 20 deselected in 3.64s
Alembic head: 0022_workflow_trigger
Real API via Backend Gate: 20 passed in 32.99s
Standalone Real API Gate: 20 passed in 33.26s
```

历史 Phase Acceptance 的结果仍按历史事实保留，不与本轮结果混淆。

## 7. 当前风险 / 未完成范围

1. 1.9-A 当前 main 的本地 Unit / Backend / PostgreSQL Migration / Real API Gate 已全部通过。
2. HALF_OPEN reservation 当前没有独立 probe token；仍需通过 1.9-B 的真实超时/并发场景验证迟到旧 Probe completion 风险。
3. Real API Gate 已通过现有 20 个真实 HTTP API 场景，但尚未等价于完成专门的 1.9-C Reliability Scenarios。
4. Frontend / Browser Reliability Convergence 尚未执行，因此不能关闭 Phase 1.9。
5. Multi-Agent orchestration、MQ/Kafka/Event Bus、Temporal/完整分布式 Worker 不属于当前已完成范围。

## 8. 下一步执行顺序

严格遵守 `docs/01-governance/DEVELOPMENT.md`：

1. **完成 1.9-B Runtime Failure / Retry / Circuit Boundary Audit。**
2. 针对 HALF_OPEN stale Probe / transaction boundary 增加真实 PostgreSQL、多 worker 测试；如验证发现 reservation 语义无法隔离 recovery window，则引入独立 probe token。
3. 完成 1.9-C Real API Reliability Scenarios。
4. 执行 Frontend Regression Gate：`npm test`、`npm run build`。
5. 执行独立 Browser E2E Gate。
6. 完成 Frontend / Backend 联调可靠性检查。
7. 最终同步 `03-acceptance/PHASE_1_9_ACCEPTANCE.md`，只有所有门禁通过后才能关闭 Phase 1.9。
8. 每个已发生并完成分析的工程错误记录到 `docs/04-errors/ERR-xxxx-description.md`。

## 9. 文档治理入口

- `docs/README.md`
- `docs/DOCS_MIGRATION_MATRIX.md`
- `docs/01-governance/DEVELOPMENT.md`
- `docs/01-governance/DOCUMENTATION.md`
- `docs/01-governance/LOCAL_TESTING.md`
- `docs/01-governance/API_TESTING.md`
- `docs/02-phases/PHASE_1_9.md`
