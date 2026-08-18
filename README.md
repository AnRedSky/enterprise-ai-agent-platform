# Enterprise AI Agent Platform

企业级 AI Agent 平台。当前统一在 `main` 分支推进，Phase 1.3 核心执行闭环已完成，正在进入 Phase 1.4 Knowledge / RAG 开发。

## 项目文档

- [完整架构与实施流程](docs/00-企业级应用%20AI%20智能体系统完整开发架构与实施流程.md)
- [开发文档](docs/DEVELOPMENT.md)
- [系统架构](docs/ARCHITECTURE.md)
- [项目开发规划](docs/07-project-development-plan.md)
- [Phase 1.4 Knowledge / RAG](docs/11-phase-1.4-knowledge-rag-plan.md)
- [本地功能测试与验收](docs/LOCAL_TESTING.md)
- [提交规范](docs/CONTRIBUTING.md)

## 当前开发状态

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

当前进入 Knowledge / RAG：

1. Knowledge Registry
2. Document / Version
3. Ingestion / Chunk
4. Retrieval contract
5. Runtime Knowledge integration
6. Vue Knowledge 管理与 Retrieval Debug

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

完整手工测试步骤请参阅 [本地功能测试与验收](docs/LOCAL_TESTING.md)。

Backend：

```powershell
cd backend
uv run pytest -q
```

Frontend：

```powershell
cd frontend
npm test
npm run build
```

前后端手工测试脚本保持独立执行。

## 配置真实模型

复制 `backend/.env.example` 为 `backend/.env`，设置：

```text
MODEL_PROVIDER=openai-compatible
MODEL_BASE_URL=https://your-provider.example/v1
MODEL_API_KEY=your-key
```

禁止将 `.env` 或任何密钥提交到 Git。
