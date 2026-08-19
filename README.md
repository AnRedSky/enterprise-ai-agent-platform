# Enterprise AI Agent Platform

企业级 AI Agent 平台。当前统一在 `main` 分支推进，Phase 1.3 核心执行闭环已完成，Phase 1.4 Knowledge / RAG 核心闭环已完成，当前主线进入 Phase 1.5 Workflow / Governance。

## 项目文档

- [完整架构与实施流程](docs/00-企业级应用%20AI%20智能体系统完整开发架构与实施流程.md)
- [开发准则](docs/DEVELOPMENT.md)
- [项目开发进度](docs/PROJECT_STATUS.md)
- [系统架构](docs/ARCHITECTURE.md)
- [项目开发规划](docs/07-project-development-plan.md)
- [Phase 1.4 Knowledge / RAG](docs/11-phase-1.4-knowledge-rag-plan.md)
- [Phase 1.4-E Vector Retrieval Provider](docs/12-phase-1.4-e-vector-retrieval-provider.md)
- [Phase 1.5 Workflow / Governance](docs/13-phase-1.5-workflow-governance-plan.md)
- [错误跟踪记录](docs/error-tracking/README.md)
- [本地功能测试与验收](docs/LOCAL_TESTING.md)
- [提交规范](docs/CONTRIBUTING.md)

## 当前开发状态

实时任务进度、阻塞项和实际测试结果统一维护在 `docs/PROJECT_STATUS.md`；长期工程规则统一维护在 `docs/DEVELOPMENT.md`。

### Phase 1.3

已形成可运行闭环：

- Identity / JWT / RBAC
- Agent Registry / AgentVersion
- Session / Message
- SSE Agent Runtime
- Model Gateway：Mock + OpenAI-compatible Provider
- Tool Registry / Runtime：Schema、权限、超时、审计基础能力
- Memory：上下文与治理基础能力
- Observability：Execution / Event / Token / Error
- Runtime / Audit：RBAC 查询、过滤、分页、Timeline
- Vue Dashboard / Agent / Runtime / Audit 管理页面
- 前端 Bearer Token 与受保护路由

### Phase 1.4

Knowledge / RAG 已完成核心闭环：

1. Knowledge Registry
2. Document / Version
3. Ingestion / Chunk
4. Retrieval contract
5. Runtime Knowledge integration
6. Vue Knowledge 管理与 Retrieval Debug
7. lexical-v2 Evaluation baseline 与本地 quality gate
8. OpenAI-compatible Embedding Provider contract 与可选真实 probe
9. provider-neutral Vector Retrieval contract 与 deterministic in-memory adapter
10. PostgreSQL + pgvector adapter 与 migration 0010
11. Runtime execution / trace 与 Retrieval Debug 关联

### Phase 1.5

当前进入 Workflow / Governance：

- 1.5-A Workflow Definition Contract：已验收
- 1.5-B Publish Governance / Tenant Contract：已通过本地 Backend 手工验收
- 1.5-C Workflow Execution State Machine：Backend Contract 已实现；当前完成 Alembic metadata 兼容问题修复，等待开发者本地重新验证

Phase 1.5-C 的历史 migration 问题与修复经验统一记录在 `docs/error-tracking/001-alembic-version-column-too-short.md`。

前后端按“后端 contract → 后端测试 → 前端 API/测试 → 联调 → Runtime 集成 → 全量回归”的顺序推进。

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

## 环境配置

后端配置模板：`backend/.env.example`；前端配置模板：`frontend/.env.example`。两个 `.env` 文件均不会提交到 Git。

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
```

Backend 使用 **uv** 管理依赖与虚拟环境，后端测试、脚本和服务运行统一使用项目 `.venv` 中的 `uv run`：

```powershell
cd backend
uv sync
uv run pytest -q
uv run alembic upgrade head
uv run python run.py
```

不要使用系统 Python 或全局 pip 安装项目运行依赖。

### Knowledge / Embedding / Vector 配置

本地 `.env` 需要按实际 Provider 补充配置；Git 只提交 `.env.example`。

Embedding：

```text
EMBEDDING_PROVIDER=none
EMBEDDING_BASE_URL=
EMBEDDING_API_KEY=
EMBEDDING_MODEL=
EMBEDDING_TIMEOUT_SECONDS=30
EMBEDDING_DIMENSION=1536
```

Vector Retrieval：

```text
VECTOR_PROVIDER=none
VECTOR_DB_URL=postgresql+asyncpg://agent:agent@localhost:5432/agent_platform
VECTOR_DB_COLLECTION=knowledge_chunks
VECTOR_TOP_K=5
VECTOR_MIN_SCORE=0.0
```

PostgreSQL / pgvector：

```text
POSTGRES_IMAGE=pgvector/pgvector:pg16
```

默认 `VECTOR_PROVIDER=none`，不会连接真实 Vector DB。启用 pgvector 时，migration 0010 要求 PostgreSQL 服务端已经安装 `vector` extension；Python / uv 环境不能替 PostgreSQL 安装 extension。推荐使用项目 Docker Compose 提供的 pgvector PostgreSQL。

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

如果本机已有 PostgreSQL 16 并通过 `DATABASE_URL` 使用它，而不是 Compose PostgreSQL，需要先在该实例安装与 PG16 匹配的 pgvector，并确认 `pg_available_extensions` 中存在 `vector`。

## 本地验收

完整手工测试步骤请参阅 [本地功能测试与验收](docs/LOCAL_TESTING.md)。

Backend：

```powershell
cd backend
uv run pytest -q
```

Phase 1.5-C Backend-only validation：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_phase_1_5_c_workflow_execution_validation.ps1
```

Vector / Embedding contract：

```powershell
cd backend
uv run pytest -q tests/test_embedding_provider.py tests/test_vector_retrieval_provider.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_embedding_provider_validation.ps1
```

pgvector schema / round-trip：

```powershell
docker compose up -d postgres redis
cd backend
uv run alembic upgrade head
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_pgvector_validation.ps1
```

Frontend：

```powershell
cd frontend
npm test
npm run build
```

Embedding Provider 本地验证未配置真实 Provider 时，脚本只执行 contract tests 并跳过真实 provider probe；配置 `EMBEDDING_PROVIDER=openai-compatible` 后才会发起真实 endpoint 请求。

当前阶段测试与质量门禁均在本地执行，暂不执行 GitHub Actions CI。

## 配置真实模型

复制 `backend/.env.example` 为 `backend/.env`，设置：

```text
MODEL_PROVIDER=openai-compatible
MODEL_BASE_URL=https://your-provider.example/v1
MODEL_API_KEY=your-key
```

如需验证真实 Embedding provider，设置：

```text
EMBEDDING_PROVIDER=openai-compatible
EMBEDDING_BASE_URL=https://your-provider.example/v1
EMBEDDING_API_KEY=your-key
EMBEDDING_MODEL=your-embedding-model
```

真实 Vector DB 接入时，再按对应 adapter 要求设置：

```text
VECTOR_PROVIDER=pgvector
VECTOR_DB_URL=postgresql+asyncpg://agent:agent@localhost:5432/agent_platform
VECTOR_DB_COLLECTION=knowledge_chunks
VECTOR_TOP_K=5
VECTOR_MIN_SCORE=0.0
```

禁止将 `.env` 或任何密钥提交到 Git。
