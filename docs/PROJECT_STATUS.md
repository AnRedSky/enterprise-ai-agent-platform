# 项目开发进度

> 本文只记录项目任务进度、实际验收结果、阻塞项和下一步任务。工程开发规则统一维护在 `docs/DEVELOPMENT.md`、`docs/DEVELOPMENT_GUIDELINES.md` 及当前补充规则文档中。阶段计划维护在对应 `docs/PHASE_*.md`。

## 1. 当前主线

- 主分支：`main`
- 项目地址：`https://github.com/AnRedSky/enterprise-ai-agent-platform.git`
- 开发方式：所有功能直接在 `main` 开发与提交
- Phase 1.5：**已完成**
- Phase 1.6：**已完成并正式关闭**
- Phase 1.7：**已完成并正式关闭**
- 当前阶段：**Phase 1.8 Event / Webhook Trigger Expansion 已正式关闭**
- 当前任务：**Phase 1.8-F Final Acceptance 已完成**
- 当前角色：开发执行
- 测试 Gate 治理：Backend、Frontend、Browser/E2E 三层独立；不使用 GitHub Actions workflow run

## 2. 阶段状态

| 阶段 | 状态 | 说明 |
|---|---|---|
| Phase 1.0 | 已完成 | 工程初始化、FastAPI + Vue |
| Phase 1.2 | 已完成 | Identity、RBAC、Agent、Session、SSE、基础 Tool |
| Phase 1.3 | 已完成 | Model Gateway、Tool Runtime、Memory、Observability、基础管理端 |
| Phase 1.4 | 已完成核心闭环 | Knowledge / RAG、pgvector、Embedding / Retrieval contract、Runtime Trace |
| Phase 1.5 | **已完成** | Workflow / Governance A～G 全部完成；Circuit Breaker 最终验收通过 |
| Phase 1.6 | **已正式关闭** | Trigger CRUD、Governance、Real HTTP、Browser E2E 全部完成 |
| Phase 1.7 | **已正式关闭** | Scheduled Trigger A～D 全部完成；Backend、Frontend、Browser 三层 Gate 通过 |
| **Phase 1.8-A** | **已完成** | Event / Webhook Trigger 需求、领域边界、Security / Idempotency、三层 Gate 已确认 |
| **Phase 1.8-B** | **已完成** | Trigger Model / Schema / Service 审计、无需 Migration、Webhook API / authentication / durable idempotency 完成 |
| **Phase 1.8-C** | **已完成** | Frontend API Types、Webhook Governance UI、Vitest、production build、Frontend Regression Gate 已通过 |
| **Phase 1.8-D** | **已完成** | Real Webhook HTTP / Runtime Boundary；accepted / duplicate / authentication / lifecycle / bounded key 全部通过 |
| **Phase 1.8-E** | **已完成** | Browser E2E 三条测试全部通过，真实 Webhook → Execution observable contract 完成 |
| **Phase 1.8-F** | **已正式关闭** | Backend / Frontend / Browser 三层 Gate 通过，验收文档与状态文档已收口 |

## 3. Phase 1.8 最终验收结果

### Backend

开发者最新实际反馈：

```text
uv run pytest -q
→ 257 passed, 20 deselected in 4.95s

scripts/test/api-real/01_run_real_api_tests.ps1
→ 20 passed in 37.94s
→ [PASS] Real API gate completed. Frontend/backend integration may proceed.
```

Phase 1.8-B 已实际执行 `uv run alembic upgrade head` 并通过；Phase 1.8 无新增数据库 Migration。

### Frontend

开发者实际反馈：

```text
npm test
→ 13 test files passed
→ 52 tests passed

npm run build
→ production build succeeded
→ 1709 modules transformed

scripts/test/release/01_frontend_regression_gate.ps1
→ Frontend automated regression passed
→ Frontend production build passed
→ [PASS] Frontend regression gate completed.
```

### Browser E2E

开发者最新实际反馈：

```text
npx playwright test --list --project="Desktop Chrome"
→ 3 tests listed

scripts/test/e2e/01_run_workflow_trigger_e2e.ps1
→ scheduled Trigger governance: passed
→ webhook Trigger governance: passed
→ webhook runtime convergence / lifecycle security: passed
→ 3 passed
→ [PASS] Phase 1.7-D browser E2E gate completed.
```

Browser Gate 为独立 Gate，不重复 Backend / Frontend regression。

## 4. Phase 1.8 核心交付

- Webhook Trigger Domain Contract。
- Webhook Trigger CRUD / enable / disable / delete。
- `POST /api/v1/webhooks/{trigger_id}` 外部事件入口。
- Secret authentication 与安全 response contract。
- 缺失事件身份 `422`。
- durable idempotency claim 与 duplicate convergence。
- bounded durable key，满足 Execution schema 100 字符边界。
- Webhook → Workflow Execution 的真实 HTTP / persistence contract。
- Frontend Webhook Governance UI / API Types。
- Browser Webhook Governance + Runtime E2E。

## 5. Database / Migration 结论

Phase 1.8 不新增数据库表或字段。

现有 `workflow_triggers` 的 `trigger_type + config + tenant/workflow/status` 已足够表达 Webhook Trigger；现有 `workflow_executions` 的 `(tenant_id, idempotency_key)` 唯一持久化边界已足够表达 Webhook durable claim。

不创建 `webhook_events` 表，不修改现有 `0022_workflow_trigger` migration。

## 6. 测试与开发治理

本项目：

1. 不提交、不触发、不依赖 GitHub Actions workflow run。
2. 所有测试由开发者在本地执行。
3. 实际测试结果只能在开发者反馈后写入状态文档。
4. Backend、Frontend、Browser/E2E 三层 Gate 独立。
5. 不提交 secret、Real API context、Playwright trace/screenshot 等本地运行产物。
6. 所有开发工作以最新 `main` 为唯一基线，禁止创建开发分支、临时分支或任务分支。

Phase 1.8 最终验收文档：`docs/PHASE_1_8_ACCEPTANCE.md`。
Phase 1.8 阶段计划：`docs/PHASE_1_8.md`。

## 7. 最终结论

**Phase 1.8 Event / Webhook Trigger Expansion 正式关闭。**

1.8-A ～ 1.8-F 全部完成，Backend / Frontend / Browser 三层本地 Gate 均已通过。

下一阶段：从最新 `main` 基线开始，先完成需求 / 架构确认与任务拆解，再进入实现；不得跳过需求确认直接扩展代码。
