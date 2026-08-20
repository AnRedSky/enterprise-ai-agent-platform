# Enterprise AI Agent Platform

企业级 AI Agent 平台。当前统一在 `main` 分支推进，Phase 1.3 核心执行闭环已完成，Phase 1.4 Knowledge / RAG 核心闭环已完成，Phase 1.5 Workflow / Governance 已完成，当前主线进入 Phase 1.6 Workflow Production Hardening。

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
- [错误跟踪记录](docs/error-tracking/README.md)
- [本地功能测试与验收](docs/LOCAL_TESTING.md)
- [提交规范](docs/CONTRIBUTING.md)

## 当前开发状态

实时任务进度、阻塞项和实际测试结果统一维护在 `docs/PROJECT_STATUS.md`；长期工程规则统一维护在 `docs/DEVELOPMENT.md`。

### Phase 1.5

Workflow / Governance 基础闭环已完成：Workflow Definition、Publish Governance、Tenant Contract、Execution State Machine、Runtime Integration、Audit / Trace、Retry / Timeout / Deadline / Circuit Breaker 均已完成并通过相应本地验收。

### Phase 1.6

当前进入 Workflow Production Hardening：

- Phase 1.6-A Workflow Trigger Contract：Backend Contract 已完成并关闭，Backend 两道 Gate 已通过开发者本地手工验收。
- Phase 1.6-B Frontend Contract / Workflow Governance UI：已实现 Frontend API Type、Vitest contract tests、Trigger Governance UI；Frontend Gate 待开发者本地执行。

Phase 1.6-B 页面入口：`/workflows/triggers`。

前后端继续严格按“后端 contract → 后端测试 → 前端 API/测试 → 前端 UI → 独立 Gate → 联调”的顺序推进。

## 前端测试目录约束

Frontend 业务源码与测试严格分离：

```text
frontend/
├── src/       # 业务源码
└── tests/     # Vitest 测试
    ├── api/
    ├── views/
    └── setup.ts
```

`frontend/src/` 禁止新增 `*.test.*`；Vitest 只执行 `frontend/tests/**/*.test.ts`。

## 测试 Gate 独立性

Backend 与 Frontend Gate 完全独立：

```text
backend/scripts/test/   # Backend 测试 Gate
frontend/scripts/test/  # Frontend 测试 Gate
```

Backend Gate 不调用 npm；Frontend Gate 不调用 uv、pytest、Alembic 或 Real API。Browser / Frontend-Backend E2E 未来作为第三独立测试层实现。

## 环境配置

后端配置模板：`backend/.env.example`；前端配置模板：`frontend/.env.example`。两个 `.env` 文件均不会提交到 Git。

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
```

Backend 使用 **uv** 管理依赖与虚拟环境，后端测试、脚本和服务运行统一使用项目 `.venv` 中的 `uv run`。

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

当前阶段测试与质量门禁均在本地执行，暂不执行 GitHub Actions CI。

## 配置真实模型

复制 `backend/.env.example` 为 `backend/.env`，设置真实 Provider 配置。禁止将 `.env` 或任何密钥提交到 Git。
