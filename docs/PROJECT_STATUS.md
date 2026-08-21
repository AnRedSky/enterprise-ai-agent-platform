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
- 当前任务：**Phase 1.8-C Frontend API Types + Governance UI 已实现，正在进入本地 Frontend Build / Gate 与 1.8-D Runtime Boundary 验收**
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
| **Phase 1.8-B** | **已完成** | Trigger Model / Schema / Service 审计、Migration 判定、Webhook API / authentication / durable idempotency 完成；本地 Backend Gate 与 Real API 已通过 |
| **Phase 1.8-C** | **实现完成，验收中** | Frontend API Types、Webhook Governance UI、Vitest 与 Browser Contract 已补齐；本次 `npm test` 已由开发者本地执行并通过 |
| **Phase 1.8-D** | **下一步** | Real Webhook HTTP / Runtime Boundary、duplicate convergence、authentication failure、disable/delete 行为验证 |
| **Phase 1.8-E** | 待 1.8-D | Browser E2E 完整 Webhook → Execution observable contract |
| **Phase 1.8-F** | 待 1.8-E | Final Acceptance / Phase 1.8 正式关闭 |

## 3. Phase 1.8-B 本地验收结果

开发者已实际反馈：

```text
uv run pytest -q
→ 255 passed, 18 deselected

uv run alembic upgrade head
→ PASS

scripts/test/api-real/01_run_real_api_tests.ps1
→ 18 passed
```

因此 Phase 1.8-B Backend Contract 已具备进入 Frontend / Runtime Boundary 的条件。

## 4. Phase 1.8-C 当前结果

已完成：

- Webhook Trigger Frontend API Types；
- Trigger inventory 中 Webhook 展示；
- Webhook Secret 创建输入 / 生成；
- `event_id_field` Contract；
- Secret 只展示配置状态，不展示 hash；
- Webhook lifecycle 操作；
- Webhook Browser Contract 测试基础；
- Frontend Vitest。

开发者本次实际反馈：

```text
npm test
→ 无异常
```

尚未将 `npm run build`、Frontend Regression Gate、完整 Webhook Browser E2E 结果标记为通过，必须等待本地实际执行反馈。

## 5. 当前测试规则

本项目不提交、不触发、不依赖 GitHub Actions workflow run。所有测试命令和验收 Gate 必须由开发者在本地执行，实际结果反馈后才能写入本状态文档。

本地 Frontend 下一步：

```powershell
cd frontend
npm run build
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

本地 Webhook Browser E2E：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

若 1.8-C 本地 Gate 通过，再进入 1.8-D Real Webhook HTTP / Runtime Boundary。

## 6. 下一步

```text
1.8-C Frontend API Types + Governance UI
        ↓
本地 Frontend Build / Regression Gate
        ↓
1.8-D Real Webhook HTTP / Runtime Boundary
        ↓
1.8-E Browser E2E
        ↓
1.8-F Final Acceptance
        ↓
Phase 1.8 正式关闭
```
