# Enterprise AI Agent Platform

企业级 AI Agent 平台。当前统一在 `main` 分支推进，正在完成 Phase 1.3 核心能力与本地验收。

## 项目文档

- [开发文档](docs/DEVELOPMENT.md)
- [系统架构](docs/ARCHITECTURE.md)
- [本地功能测试与验收](docs/LOCAL_TESTING.md)
- [提交规范](docs/CONTRIBUTING.md)

## Phase 1.2

已完成：
- Alembic 初始数据库迁移
- User / Role / UserRole + JWT 认证
- RBAC 基础权限
- Agent Registry + AgentVersion
- Session / Message 持久化
- SSE Agent Runtime
- request_id / trace_id / execution_id / session_id / agent_version / model_id
- Model Gateway + Mock Provider
- Tool Registry 基础 API
- AuditLog 数据模型
- pytest 单元测试
- GitHub Actions CI

## Phase 1.3 当前进展

已实现并进入验收：
- Model Gateway Provider contract
- OpenAI-compatible Provider
- 非流式 / SSE 流式模型调用
- Token Usage 标准结果结构
- Agent Runtime 与 Model Provider 解耦
- Tool Runtime 基础安全边界、超时与审计
- Memory 上下文与治理基础能力
- Observability Execution / Event / Token / Error 链路
- Runtime / Audit RBAC 查询与稳定分页
- Vue Dashboard / Agent / Runtime / Audit 基础管理页面
- Vue 登录、Bearer Token 注入与受保护路由

## 环境配置

后端配置模板：`backend/.env.example`；前端配置模板：`frontend/.env.example`。两个 `.env` 文件均不会提交到 Git。

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
```

后端 `.env` 可直接修改 `APP_HOST`、`APP_PORT`、`CORS_ORIGINS`、数据库、Redis、JWT 和模型配置；前端 `.env` 可修改 `VITE_API_BASE_URL`、`VITE_DEV_HOST`、`VITE_DEV_PORT`。

## 本地启动

```bash
docker compose up -d postgres redis
cd backend
uv sync
uv run alembic upgrade head
uv run python run.py
```

`run.py` 会读取 `backend/.env` 中的 `APP_HOST` / `APP_PORT`。API 默认：`http://localhost:8000/docs`

前端：

```bash
cd frontend
npm install
npm run dev
```

前端开发服务会读取 `frontend/.env` 中的 `VITE_DEV_HOST` / `VITE_DEV_PORT`。

## 本地验收

完整手工测试步骤请参阅 [本地功能测试与验收](docs/LOCAL_TESTING.md)。

自动化测试：

```bash
cd backend
uv run pytest -q

cd ../frontend
npm test
npm run build
```

## 配置真实模型

复制 `backend/.env.example` 为 `backend/.env`，设置：

```text
MODEL_PROVIDER=openai-compatible
MODEL_BASE_URL=https://your-provider.example/v1
MODEL_API_KEY=your-key
```

禁止将 `.env` 或任何密钥提交到 Git。
