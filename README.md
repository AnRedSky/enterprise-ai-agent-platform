# Enterprise AI Agent Platform

企业级 AI Agent 平台，当前开发主线：`feature/phase-1.2`。

## Phase 1.2

已完成：
- Alembic 初始数据库迁移
- User / Role / UserRole + JWT 认证
- Agent Registry + AgentVersion
- Session / Message 持久化
- SSE Agent Runtime
- request_id / trace_id / execution_id / session_id / agent_version / model_id
- Model Gateway + Mock Provider
- Tool Registry 基础 API
- AuditLog 数据模型
- pytest 单元测试
- GitHub Actions CI

## 本地启动

```bash
docker compose up -d postgres redis
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

API: `http://localhost:8000/docs`

## 流式调用

`POST /api/v1/agents/stream`

```json
{
  "agent_id": "<agent-id>",
  "input": "你好"
}
```

使用 `Authorization: Bearer <token>`。

## 下一阶段

Phase 1.3 将重点进入真实模型 Provider、Tool 执行沙箱、Memory、Observability，以及 Vue 管理端完整接入。
