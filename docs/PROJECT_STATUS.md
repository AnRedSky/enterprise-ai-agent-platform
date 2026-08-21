# 项目开发进度

> 本文只记录项目任务进度、实际验收结果、阻塞项和下一步任务。工程开发规则统一维护在 `docs/DEVELOPMENT.md` 及其当前补充规则文档中。阶段计划维护在对应 `docs/PHASE_*.md`。

## 1. 当前主线

- 主分支：`main`
- 项目地址：`https://github.com/AnRedSky/enterprise-ai-agent-platform.git`
- 开发方式：所有功能直接在 `main` 开发与提交
- Phase 1.5：**已完成**
- Phase 1.6：**已完成并正式关闭**
- Phase 1.7：**已完成并正式关闭**
- 当前阶段：**Phase 1.8 Event / Webhook Trigger Expansion**
- 当前任务：**Phase 1.8-D Real Webhook HTTP / Runtime Boundary 已进入实现与本地验收；1.8-C Frontend Build / Regression Gate 已由开发者本地通过**
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
| **Phase 1.8-B** | **已完成** | Trigger Model / Schema / Service 审计、无需 Migration、Webhook API / authentication / durable idempotency 完成；本地 Backend Gate 与 Real API 已通过 |
| **Phase 1.8-C** | **已完成** | Frontend API Types、Webhook Governance UI、Vitest、production build、Frontend Regression Gate 已通过 |
| **Phase 1.8-D** | **实现与验收中** | Real Webhook HTTP / Runtime Boundary；补齐 missing identity、bounded durable key、duplicate convergence、authentication、disable/delete 的 Real API 覆盖 |
| **Phase 1.8-E** | 待 1.8-D | Browser E2E 完整 Webhook → Execution observable contract |
| **Phase 1.8-F** | 待 1.8-E | Final Acceptance / Phase 1.8 正式关闭 |

## 3. Phase 1.8-B 本地验收结果

开发者实际反馈：

```text
uv run pytest -q
→ 257 passed, 18 deselected in 4.11s

scripts/test/api-real/01_run_real_api_tests.ps1
→ 18 passed in 30.47s
→ [PASS] Real API gate completed. Frontend/backend integration may proceed.
```

此前 `uv run alembic upgrade head` 已实际通过；本轮反馈未重复执行 Migration，因此不将本轮 Migration 标记为新执行结果。

## 4. Phase 1.8-C 本地验收结果

已完成：

- Webhook Trigger Frontend API Types；
- Trigger inventory 中 Webhook 展示；
- Webhook Secret 创建输入 / 生成；
- `event_id_field` Contract；
- Secret 只展示配置状态，不展示 hash；
- Webhook lifecycle 操作；
- Webhook Browser Contract 测试基础；
- Frontend Vitest。

开发者最新实际反馈：

```text
npm run build
→ vite production build succeeded
→ 1709 modules transformed
→ built in 4.15s

scripts/test/release/01_frontend_regression_gate.ps1
→ Frontend automated regression: 13 test files passed, 52 tests passed
→ Frontend production build: succeeded
→ [PASS] Frontend regression gate completed.
```

上述结果为开发者本地实际执行结果，已满足 1.8-C Gate，不再将 1.8-C 标记为验收中。

## 5. Phase 1.8-D 当前结果

本批在 `main` 上补齐 Real API / Runtime Boundary 测试覆盖：

- Webhook 合法请求 → durable Workflow Execution；
- duplicate event → 同一 Execution；
- invalid secret → `401`；
- disabled Trigger → `409`；
- deleted Trigger → `404`；
- 缺失 `Idempotency-Key` 且 payload 缺失配置事件字段 → `422`；
- 100 字符事件身份触发 bounded durable idempotency key，并验证长度为 `webhook:` + SHA-256 64 hex；
- duplicate 对 bounded key 再次投递保持同一 Execution。

本批代码已提交，但**尚未声称 Real API Gate 通过**；必须由开发者本地执行后记录实际结果。

## 6. 当前测试规则

本项目不提交、不触发、不依赖 GitHub Actions workflow run。所有测试命令和验收 Gate 必须由开发者在本地执行，实际结果反馈后才能写入本状态文档。

### Phase 1.8-D 本地验收

```powershell
cd backend
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

如果本批涉及 Migration，另执行：

```powershell
uv run alembic upgrade head
```

本批没有新增数据库 Migration，因此不要求重复创建 Migration；但 Backend Gate 的既定 Migration/head verification 仍以开发者本地 Gate 流程为准。

### Phase 1.8-E Browser E2E

```powershell
cd frontend
npx playwright test --list --project="Desktop Chrome"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

Browser E2E 作为独立 Gate，不复制 Backend / Frontend regression。

## 7. 下一步

```text
1.8-D Real Webhook HTTP / Runtime Boundary
        ↓
本地 Backend default regression + Real API Gate
        ↓
1.8-E Browser E2E
        ↓
1.8-F Final Acceptance
        ↓
Phase 1.8 正式关闭
```
