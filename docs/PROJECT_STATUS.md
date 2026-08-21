# Project Status

> 当前项目状态唯一入口。文档治理规则见 `docs/01-governance/DOCUMENTATION.md`，工程开发规则见 `docs/01-governance/DEVELOPMENT.md`。

## 1. 当前基线

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 开发原则：所有任务直接基于最新 `main`，禁止 feature / task / 临时分支。
- 当前文档治理：Docs Governance Refactor 第二阶段已完成。

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
| Retry / Timeout / Idempotency / Deadline | 已实现当前历史范围 | Phase 1.5-F 已形成基础 Contract，但需要在当前 Reliability 阶段重新验证跨边界行为 |
| Circuit Breaker | **正在修复** | 当前代码审查发现 HALF_OPEN 多 Probe 成功/失败的并发恢复语义缺口；1.9-A 已开始修复并补测试 |
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
| **Phase 1.9** | **进行中** | Runtime Reliability / Production Hardening |

## 4. Phase 1.9 当前任务

### 1.9-A Circuit Breaker HALF_OPEN Concurrent Recovery

当前代码审查发现：原 `CircuitBreakerService.record_success()` 在 HALF_OPEN 状态下会在任意一个 Probe 成功后立即关闭 Circuit；当 `half_open_max_calls > 1` 且其他 Probe 仍在执行时，这可能导致一个成功 Probe 抢先恢复 Circuit，而另一个并发 Probe 随后失败，造成恢复状态不符合当前 Probe 窗口的并发语义。

已完成：

- `backend/app/services/circuit_breaker.py`：将 HALF_OPEN `success_count` 明确作为活动 Probe reservation 数量；成功只释放一个 reservation；仅当当前 recovery window 无 outstanding Probe 时关闭 Circuit。
- 新增 `backend/tests/unit/test_circuit_breaker_half_open_concurrency.py`，覆盖多 Probe 成功、并发 Probe 失败重新 OPEN 等边界。
- 已建立 `docs/02-phases/PHASE_1_9.md`。

待执行：

```powershell
cd backend
uv run pytest -q backend/tests/unit/test_circuit_breaker.py backend/tests/unit/test_circuit_breaker_half_open_concurrency.py
```

然后依次执行完整 Backend Gate、Alembic head、Real API Gate；测试结果必须使用开发者本地实际反馈更新。

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

## 6. 历史实际测试结果

历史 Acceptance 中的实际结果继续保留，迁移不改变事实。例如 Phase 1.8 原验收记录：

```text
Backend pytest: 257 passed, 20 deselected in 4.95s
Real API: 20 passed in 37.94s
Frontend: 52 tests passed / build succeeded
Browser E2E: 3 passed
```

这些是历史实际结果，不是本次 Phase 1.9 修复后的新测试结果。fileciteturn372file0L2-L2

## 7. 当前风险 / 未完成范围

1. Circuit Breaker HALF_OPEN 并发恢复正在修复，尚未完成当前 main 的本地 Gate。
2. Real API / Provider 的真实语义质量必须继续以实际本地 Provider 反馈为准，不能用 Mock Embedding 质量替代。
3. Multi-Agent orchestration、MQ/Kafka/Event Bus、Temporal/完整分布式 Worker 不属于当前已完成范围。
4. Phase 1.9-B/C/D 尚未执行，因此不能宣称当前全系统已经完成生产级 Reliability Acceptance。

## 8. 下一步执行顺序

严格遵守 `docs/01-governance/DEVELOPMENT.md`：

1. 最新 `main` 基线。
2. 完成 1.9-A Circuit Breaker HALF_OPEN 并发修复的本地单元测试。
3. 执行 Alembic head 与完整 Backend Gate。
4. 执行 Real API Gate，验证 OPEN/HALF_OPEN、Retry/Deadline/Idempotency 边界。
5. 完成 1.9-B Runtime Failure / Retry / Circuit Boundary Audit。
6. 完成 1.9-C Real API Reliability Scenarios。
7. 完成 1.9-D Frontend / Browser Reliability Convergence。
8. Backend / Frontend / Browser 三层独立 Gate。
9. 更新 `03-acceptance/PHASE_1_9_ACCEPTANCE.md` 并关闭 Phase 1.9。
10. 每个已发生并完成分析的工程错误记录到 `docs/04-errors/ERR-xxxx-description.md`。

## 9. 文档治理入口

- `docs/README.md`
- `docs/DOCS_MIGRATION_MATRIX.md`
- `docs/01-governance/DEVELOPMENT.md`
- `docs/01-governance/DOCUMENTATION.md`
- `docs/01-governance/LOCAL_TESTING.md`
- `docs/01-governance/API_TESTING.md`
- `docs/02-phases/PHASE_1_9.md`
