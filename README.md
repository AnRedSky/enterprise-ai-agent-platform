# Enterprise AI Agent Platform

企业级 AI Agent 平台。当前统一在 `main` 分支推进。Phase 1.x、Phase 2.1、Phase 2.2、Phase 2.3、Phase 2.5 已正式关闭；当前已完成 **Phase 2.7 Advanced Workflow Orchestration 主线生产开发，进入本地测试、回归修复与验收阶段**。

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
- [Phase 2.1 Organization](docs/02-phases/PHASE_2_1.md)
- [Phase 2.2 Retrieval Production Quality](docs/02-phases/PHASE_2_2.md)
- [Phase 2.2 Acceptance](docs/03-acceptance/PHASE_2_2_ACCEPTANCE.md)
- [Phase 2.3 Model Provider Governance](docs/02-phases/PHASE_2_3.md)
- [错误记录](docs/04-errors/)

## 当前开发状态

实时任务进度、阻塞项和实际测试结果统一维护在 `docs/PROJECT_STATUS.md`；长期工程规则统一维护在 `docs/01-governance/DEVELOPMENT.md`。当前主线生产开发阶段为 **Phase 2.7 Advanced Workflow Orchestration**，目前处于本地回归修复与验收准备。

### Phase 2.7 当前执行顺序

```text
2.7 主线生产实现                 ← 已完成
        ↓
本地 Unit / Default Regression   ← 当前
        ↓
Migration / DB verification
        ↓
Real HTTP API Gate
        ↓
Frontend Gate
        ↓
Browser / Frontend-Backend E2E（如范围涉及）
        ↓
本地手动场景
        ↓
Acceptance / Status / Error Records
```

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

基础设施：

```powershell
docker compose up -d postgres redis
```

Backend API Service：

```powershell
cd backend
uv sync
uv run alembic upgrade head
uv run python run.py
```

Scheduler Service 必须作为独立进程启动：

```powershell
cd backend
uv run python run_scheduler.py
```

API 默认：`http://localhost:8000/docs`

前端：

```powershell
cd frontend
npm install
npm run dev
```

## 本地回归

Backend 默认回归：

```powershell
cd backend
uv run pytest -q
```

Backend Release / Regression Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

Backend Manual API：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\dev\run_manual_test_suite.ps1 -Mode api
```

Workflow Retry / Timeout / Runtime 定向回归：

```powershell
cd backend
uv run pytest -q tests/unit/test_workflow_retry_budget.py tests/unit/test_workflow_runtime_timeout.py tests/unit/test_workflow_runtime.py
```

## 当前真实测试结果

2026-08-28 开发者本地实际反馈：

```text
uv run pytest -q tests/unit
94 failed, 622 passed, 2 warnings
```

Workflow Retry / Timeout / Runtime 定向测试：

```text
5 failed, 14 passed
```

本轮已修复的生产问题包括 Retry Budget / Workflow Deadline 的耗尽治理事实，以及 DAG 单 root 首次执行不应产生 Branch State。其余失败按当前 Durable Frontier、Checkpoint、Resume、Recovery、tenant boundary、worker fencing 与 DAG Contract 继续收敛测试 double / fixture，不放宽正式生产 Contract。

具体错误记录见 `docs/04-errors/2026-08-28-phase-2-7-local-regression-retry-governance-and-dag-root-state.md`。

未实际执行的 Gate 不得记录为通过。
