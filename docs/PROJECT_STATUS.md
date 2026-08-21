# 项目开发进度

> 本文只记录项目任务进度、实际验收结果、阻塞项和下一步任务。
> 工程开发规则统一维护在 `docs/DEVELOPMENT.md`，不得在本文件复制或替代开发准则。

## 1. 当前主线

- 主分支：`main`
- 项目地址：`https://github.com/AnRedSky/enterprise-ai-agent-platform.git`
- 开发方式：所有功能直接在 `main` 开发与提交
- Phase 1.5：**已完成**
- 当前阶段：**Phase 1.6 Workflow Production Hardening**
- 当前任务：**Phase 1.6-C Frontend / Backend Integration & Browser E2E Contract**
- 当前角色：开发执行
- 测试 Gate 治理：Backend、Frontend、Browser/E2E 三层独立
- 规范核查：已完成，详见 `docs/14-project-compliance-audit-and-correction-plan.md`

## 2. 阶段状态

| 阶段 | 状态 | 说明 |
|---|---|---|
| Phase 1.0 | 已完成 | 工程初始化、FastAPI + Vue |
| Phase 1.2 | 已完成 | Identity、RBAC、Agent、Session、SSE、基础 Tool |
| Phase 1.3 | 已完成 | Model Gateway、Tool Runtime、Memory、Observability、基础管理端 |
| Phase 1.4 | 已完成核心闭环 | Knowledge / RAG、pgvector、Embedding / Retrieval contract、Runtime Trace |
| Phase 1.5-A | 已完成 | Workflow Definition Contract，本地 Backend 验收通过 |
| Phase 1.5-B | 已完成 | Publish Governance、Tenant Contract，本地 Backend 手工验收通过 |
| Phase 1.5-C | 已完成 | Workflow Execution State Machine，本地 Backend 验收通过 |
| Phase 1.5-D | 已完成 | Workflow Runtime Integration；本地验收无异常 |
| Phase 1.5-E | 已完成 | Governance / Audit / Trace；全量测试通过，warning 已修复并验收通过 |
| Phase 1.5-F | 已完成 | Cancel / Retry / Retry lineage / Idempotency-Key / Execution Concurrency / Timeout / Failure Recovery / Node Retry / Attempt / Retry Budget / Workflow Deadline 治理已完成并通过 Real API 边界验收 |
| Phase 1.5-G | **已完成** | Circuit Breaker 治理完成；Backend pytest、migration/head、Real API Gate 全部通过 |
| Phase 1.5 | **已完成** | A～G 全部完成；不再重复开发 Circuit Breaker |
| 测试基础设施治理 | 已修复 | Backend / Frontend Gate 已拆分，测试脚本归属正确 |
| Phase 1.6-A | **已完成** | Workflow Trigger Backend Contract；Backend Domain / API / Migration / Contract / Real API 两道 Gate 已由开发者本地手工验收通过 |
| Phase 1.6-B | **已完成** | Frontend API Type / Vitest / Workflow Trigger Governance UI 已实现；Frontend Vitest、production build、Trigger Real HTTP、UI 手动验收已通过 |
| Phase 1.6-C | **开发中** | Browser / Frontend-Backend E2E 第三独立测试层已建立，等待开发者本地执行 E2E Gate |

## 3. 测试 Gate 结构

```text
Backend Gate（独立）
Backend regression → Migration/head → Real API

Frontend Gate（独立）
Frontend test → production build

E2E Gate（独立第三层）
Browser → real Frontend → real Backend HTTP
```

E2E 不复制 Backend 或 Frontend 现有 Gate。

## 4. Phase 1.6-A / 1.6-B 实际验收摘要

### Phase 1.6-A

```text
Backend pytest / Migration / Real API
→ Phase 1.6-A Backend Contract 正式关闭
```

Trigger Contract 包含：

- WorkflowTrigger domain model 与 Tenant / Workflow scope。
- Migration `0022_workflow_trigger`。
- Trigger CRUD、manual invoke、enabled/disabled、Published Workflow 校验。
- Idempotency-Key 复用 Workflow Execution 治理。
- Trigger identity 写入 Audit metadata / Trace data。

### Phase 1.6-B

已完成：

- `frontend/src/api/workflows.ts`
- `frontend/src/views/workflow-triggers/index.vue`
- `frontend/src/router/index.ts`
- `frontend/tests/api/workflows.test.ts`
- `frontend/tests/views/WorkflowTriggers.test.ts`
- `frontend/scripts/test/api-real/01_run_trigger_http_contract.ps1`

开发者反馈的最终结果：

```text
Frontend Vitest             PASS — 50 passed
Frontend production build   PASS
Backend Real API            PASS — 14 passed
Frontend Trigger HTTP       PASS（手动测试）
Frontend UI 手动验收         PASS
```

因此 Phase 1.6-B 正式关闭。

## 5. Phase 1.6-C 当前实现

已建立第三独立 E2E 层：

```text
frontend/playwright.config.ts
frontend/tests/e2e/workflow-trigger-governance.spec.ts
frontend/scripts/test/e2e/01_run_workflow_trigger_e2e.ps1
```

`frontend/package.json` 增加：

```text
@playwright/test
npm run test:e2e
```

E2E 真实用户链路覆盖：

```text
注册隔离用户
→ Backend 创建 Published Workflow fixture
→ Browser 登录
→ Workflow Trigger Governance
→ 创建 manual Trigger
→ Invoke
→ completed Execution
→ Disable
→ UI 禁止 Invoke
→ Enable
→ Delete
```

当前状态：**实现完成，E2E 尚未执行，不得标记通过。**

## 6. Phase 1.6-C 本地执行要求

首次安装：

```powershell
cd frontend
npm install
npx playwright install chromium
```

启动 Backend：

```powershell
cd backend
uv run python run.py
```

启动 Frontend：

```powershell
cd frontend
npm run dev
```

执行 E2E Gate：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

可选环境变量：

```text
FRONTEND_BASE_URL=http://127.0.0.1:5173
API_BASE_URL=http://127.0.0.1:8000/api/v1
```

## 7. 下一步关闭条件

Phase 1.6-C 关闭前必须以开发者本地实际结果为准完成：

1. Browser E2E Gate。
2. Backend Gate。
3. Frontend Gate。
4. 更新本文件与 `docs/17-phase-1.6-c-frontend-backend-e2e-contract.md`。
5. 若出现工程错误，记录到 `docs/error-tracking/`。
6. 提交 `main`。

E2E Gate 通过前，不进入下一 Phase 的业务功能扩展。
