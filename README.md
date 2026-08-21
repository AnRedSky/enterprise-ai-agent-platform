# Enterprise AI Agent Platform

企业级 AI Agent 平台。当前统一在 `main` 分支推进，Phase 1.3 核心执行闭环已完成，Phase 1.4 Knowledge / RAG 核心闭环已完成，Phase 1.5 Workflow / Governance 已完成，Phase 1.6 Workflow Production Hardening 已正式关闭，当前推进 Phase 1.7 Workflow Trigger Expansion / Scheduling Contract。

## 项目文档

- [完整架构与实施流程](docs/00-企业级应用%20AI%20智能体系统完整开发架构与实施流程.md)
- [开发准则](docs/DEVELOPMENT.md)
- [项目开发进度](docs/PROJECT_STATUS.md)
- [系统架构](docs/ARCHITECTURE.md)
- [项目开发规划](docs/07-project-development-plan.md)
- [Phase 1.4 Knowledge / RAG](docs/11-phase-1.4-knowledge-rag-plan.md)
- [Phase 1.4-E Vector Retrieval Provider](docs/12-phase-1.4-e-vector-retrieval-provider.md)
- [Phase 1.5 Workflow / Governance](docs/13-phase-1.5-workflow-governance-plan.md)
- [Phase 1.6 Workflow Production Hardening](docs/15-phase-1.6-workflow-production-hardening-plan.md)
- [Phase 1.6-B Frontend Workflow Governance UI](docs/16-phase-1.6-b-frontend-workflow-governance-ui-contract.md)
- [Phase 1.6-C Frontend / Backend E2E](docs/17-phase-1.6-c-frontend-backend-e2e-contract.md)
- [Phase 1.7 Workflow Trigger Scheduling Contract](docs/18-phase-1.7-workflow-trigger-scheduling-contract.md)
- [Phase 1.7-C Schedule Governance / Frontend Integration](docs/19-phase-1.7-c-schedule-governance-frontend-integration.md)
- [错误跟踪记录](docs/error-tracking/README.md)
- [本地功能测试与验收](docs/LOCAL_TESTING.md)
- [提交规范](docs/CONTRIBUTING.md)

## 当前开发状态

实时任务进度、阻塞项和实际测试结果统一维护在 `docs/PROJECT_STATUS.md`；长期工程规则统一维护在 `docs/DEVELOPMENT.md`。

### Phase 1.5

Workflow / Governance 基础闭环已完成：Workflow Definition、Publish Governance、Tenant Contract、Execution State Machine、Runtime Integration、Audit / Trace、Retry / Timeout / Deadline / Circuit Breaker 均已完成并通过相应本地验收。

### Phase 1.6

Workflow Production Hardening 已正式关闭：

- Phase 1.6-A Backend Trigger Contract 已关闭。
- Phase 1.6-B Frontend Workflow Governance UI Contract 已关闭。
- Phase 1.6-C Browser / Frontend-Backend E2E Contract 已关闭。
- Backend Real API：14 passed。
- Frontend Vitest：50 passed。
- Frontend production build：PASS。
- Browser E2E：1 passed。

### Phase 1.7

当前推进 Workflow Trigger Expansion / Scheduling Contract：

- Phase 1.7-A：Scheduled Trigger Backend / Scheduler / Recovery 基线审计完成，确认已有实现，不重复建设。
- Phase 1.7-B：Scheduler execution / persistence integration 的 current/recovery persistence Real API Gate 已通过；Runtime failure persistence 专项仍待完成。
- Phase 1.7-C：Schedule Governance / Frontend Integration 已开始实施。
- Phase 1.7-D：Real HTTP + Browser E2E scheduling contract，待 C 阶段 Frontend Gate 验收后推进。

Scheduled Trigger 当前前后端统一使用 `timezone + interval_seconds` Contract；前端不实现 scheduler slot、recovery、lease、worker coordination 或 next-run 计算。

## 前端测试目录约束

Frontend 业务源码与测试严格分离：

```text
frontend/
├── src/       # 业务源码
└── tests/     # Vitest / Browser E2E 测试
```

Frontend 单元 / UI 测试统一位于 `frontend/tests/`；`frontend/src/` 禁止新增 `*.test.*`。

## 测试 Gate 独立性

Backend、Frontend、Browser/E2E 三层 Gate 完全独立：

```text
backend/scripts/test/   # Backend Gate
frontend/scripts/test/  # Frontend Gate
frontend/scripts/test/e2e/  # Browser / Frontend-Backend E2E Gate
```

E2E 不复制 Backend regression、Migration、Real API 或 Frontend regression。

## 环境配置

后端配置模板：`backend/.env.example`；前端配置模板：`frontend/.env.example`。两个 `.env` 文件均不会提交到 Git。

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
```

Backend 使用 **uv** 管理依赖与虚拟环境；后端测试、脚本和服务运行统一使用项目 `.venv` 中的 `uv run`。

## 本地启动

```bash
docker compose up -d postgres redis
cd backend
uv sync
uv run alembic upgrade head
uv run python run.py
```

API 默认：`http://localhost:8000/docs`

前端：

```bash
cd frontend
npm install
npm run dev
```

## 本地验收

Backend：

```powershell
cd backend
uv run pytest -q
uv run alembic upgrade head
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

Frontend：

```powershell
cd frontend
npm test
npm run build
```

Frontend 独立 Regression Gate：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

Browser E2E：

```powershell
cd frontend
npx playwright test --list --project="Desktop Chrome"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```
