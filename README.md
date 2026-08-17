# Enterprise AI Agent Platform

企业级 AI Agent 平台。当前开发主线：`feature/phase-1.2`，正在推进 Phase 1.3。

## 项目文档

- [开发文档](docs/DEVELOPMENT.md)
- [系统架构](docs/ARCHITECTURE.md)
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

- Model Gateway Provider contract
- OpenAI-compatible Provider
- 非流式 / SSE 流式模型调用
- Token Usage 标准结果结构
- Agent Runtime 与 Model Provider 解耦

后续依次实现 Tool Runtime、Memory、Observability 和 Vue 管理端完整接入。

## 本地启动

```bash
docker compose up -d postgres redis
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

API: `http://localhost:8000/docs`

## 配置真实模型

复制 `.env.example` 为 `.env`，设置：

```text
MODEL_PROVIDER=openai-compatible
MODEL_BASE_URL=https://your-provider.example/v1
MODEL_API_KEY=your-key
```

禁止将 `.env` 或任何密钥提交到 Git。
