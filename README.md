# Enterprise AI Agent Platform

企业级 AI Agent 平台。当前统一在 `main` 分支推进。Phase 1.x、Phase 2.1 与 **Phase 2.2 Retrieval Production Quality 已正式关闭**；当前进入 **Phase 2.3 Model Provider Governance**。

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

实时任务进度、阻塞项和实际测试结果统一维护在 `docs/PROJECT_STATUS.md`；长期工程规则统一维护在 `docs/01-governance/DEVELOPMENT.md`。当前阶段为 **Phase 2.3**。新阶段必须先经过产品需求与架构决策，不得凭空创建新的 Phase。

### Phase 2.3 当前执行顺序

```text
2.3-A Provider Governance Contract  ← 当前已完成
        ↓
2.3-B Backend Domain + API Contract
        ↓
2.3-C Migration + Backend Tests（若需要持久化）
        ↓
2.3-D Real API / Integration
        ↓
2.3-E / F Frontend（若范围涉及 UI）
        ↓
2.3-G / H Backend + Frontend Gates
        ↓
2.3-I Browser E2E（若涉及用户链路）
        ↓
2.3-J Acceptance / Status / Error Records
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

## Phase 2.3-A 本地验收固定入口

本次新增 Contract 是纯 Backend domain logic，不涉及数据库、Frontend 或 Browser，因此先执行 targeted unit test：

```powershell
cd backend
uv run pytest -q tests/unit/test_model_provider_governance_contract.py
```

完成 2.3-B 后，再按开发准则补充对应 API Contract / Real API；未实际执行的结果不得记录为通过。
