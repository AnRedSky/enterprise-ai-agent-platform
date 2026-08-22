# Enterprise AI Agent Platform

企业级 AI Agent 平台。当前统一在 `main` 分支推进，Phase 1.3 核心执行闭环、Phase 1.4 Knowledge / RAG、Phase 1.5 Workflow / Governance、Phase 1.6 Trigger Contract、Phase 1.7 Scheduling、Phase 1.8 Webhook / Event Trigger 与 Phase 1.9 Runtime Reliability / Production Hardening 均已完成当前定义范围；**Phase 1.9 已正式关闭，新 Phase 尚未立项**。

## 项目文档

- [产品能力基线](docs/PRODUCT_CAPABILITY_BASELINE.md)
- [产品与功能开发对比矩阵](docs/PRODUCT_DEVELOPMENT_MATRIX.md)
- [完整架构与实施流程](docs/00-企业级应用%20AI%20智能体系统完整开发架构与实施流程.md)
- [开发准则](docs/01-governance/DEVELOPMENT.md)
- [项目开发进度](docs/PROJECT_STATUS.md)
- [系统架构](docs/00-architecture/SYSTEM_ARCHITECTURE.md)
- [Observability 架构](docs/00-architecture/OBSERVABILITY_ARCHITECTURE.md)
- [文档治理](docs/01-governance/DOCUMENTATION.md)
- [Phase 1.3 Model Gateway / Tool Runtime / Memory / Observability](docs/02-phases/PHASE_1_3.md)
- [Phase 1.4 Knowledge / RAG / Retrieval](docs/02-phases/PHASE_1_4.md)
- [Phase 1.5 Workflow / Governance](docs/02-phases/PHASE_1_5.md)
- [Phase 1.6 Trigger Contract](docs/02-phases/PHASE_1_6.md)
- [Phase 1.7 Scheduling](docs/02-phases/PHASE_1_7.md)
- [Phase 1.8 Webhook / Event Trigger](docs/02-phases/PHASE_1_8.md)
- [Phase 1.9 Runtime Reliability](docs/02-phases/PHASE_1_9.md)
- [错误记录](docs/04-errors/)

## 当前开发状态

实时任务进度、阻塞项和实际测试结果统一维护在 `docs/PROJECT_STATUS.md`；长期工程规则统一维护在 `docs/01-governance/DEVELOPMENT.md`。当前状态为 **Phase 1.9 已完成 / 正式关闭**，后续新阶段必须先经过产品需求与架构决策，不得凭空创建 Phase 2。

### Phase 1.x 产品闭环

```text
Identity / RBAC
      ↓
Agent / Session / Runtime
      ↓
Model Gateway ── Tool Runtime ── Memory ── Observability
      ↓
Knowledge / RAG / Retrieval
      ↓
Workflow / Governance
      ↓
Trigger Contract
   ┌──┴─────────────┐
Scheduled        Webhook
   └──┬─────────────┘
      ↓
Runtime Reliability / Production Hardening
```

### 最新 Phase 1.9 本地验收基线

- Backend：264 passed，23 deselected。
- Migration：`0022_workflow_trigger` 为 head。
- Real API：23 passed。
- Frontend：13 test files / 52 tests passed，production build passed。
- Browser：Desktop Chrome 3 passed。

这些是 Phase 1.9 Acceptance 已记录的实际本地证据；新任务不得将其描述成当前重新执行的测试。

## 当前明确产品边界

当前 Phase 文档明确未覆盖、且未正式立项的能力包括：

- MQ / Kafka / 通用 Event Bus；
- Temporal / Airflow 等分布式 Workflow Engine；
- 复杂 DAG、Saga、复杂 Policy DSL；
- Multi-Agent orchestration；
- 可视化拖拽 Workflow Designer；
- 任意代码执行；
- 完整企业 IAM / Organization；
- 完整分布式 Scheduler（lease、misfire、独立 scheduler state 等）；
- 真实 Embedding Provider 语义质量的最终产品结论。

这些属于产品决策候选项，不自动等同下一阶段开发任务。

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
backend/scripts/test/       # Backend Gate
frontend/scripts/test/      # Frontend Gate
frontend/scripts/test/e2e/  # Browser / Frontend-Backend E2E Gate
```

E2E 不复制 Backend regression、Migration、Real API 或 Frontend regression。

## 环境配置

后端配置模板：`backend/.env.example`；前端配置模板：`frontend/.env.example`。两个 `.env` 文件均不会提交到 Git。

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
```

Backend 使用 **uv** 管理依赖与虚拟环境；后端测试、脚本和服务运行统一使用 `uv run`。

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

## 本地验收固定入口

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
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

Browser E2E：

```powershell
cd frontend
npx playwright test --list --project="Desktop Chrome"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

以上 Gate 必须按 `docs/01-governance/DEVELOPMENT.md` 保持独立；未实际执行的测试不得写成通过。
