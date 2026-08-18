# API 接口单元测试与本地手工验收

当前 `main` 已为后端 HTTP API 增加按模块拆分的 pytest 脚本。现有 API 模块包含 auth、agents、chat、runtime、tools，以及 `/health`；对应测试文件分别覆盖路由注册、认证边界和基础响应契约。

## 1. 自动化接口测试

在 `backend` 目录执行：

```powershell
uv run pytest tests/test_api_health_endpoint.py -q
uv run pytest tests/test_api_auth_endpoints.py -q
uv run pytest tests/test_api_agents_endpoints.py -q
uv run pytest tests/test_api_chat_endpoints.py -q
uv run pytest tests/test_api_runtime_endpoints.py -q
uv run pytest tests/test_api_tools_endpoints.py -q
```

全部执行：

```powershell
uv run pytest -q
```

这些测试主要保证 API 路由没有丢失，并验证受保护接口在没有 Bearer Token 时返回 `401`。业务层和 RBAC 深度测试仍保留在原有 `test_runtime_*`、`test_tool_*` 等测试中。

## 2. 本地手工测试准备

启动基础服务：

```powershell
docker compose up -d postgres redis
```

启动后端：

```powershell
cd backend
uv run alembic upgrade head
uv run python run.py
```

启动前端：

```powershell
cd frontend
npm run dev
```

默认：

- Backend: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Frontend: `http://localhost:5173`

如果 `.env` 修改了端口，以实际配置为准。

## 3. 手工 API 测试顺序

### A. Health

`GET /health`

预期：HTTP `200`，响应包含：

```json
{"status":"ok","version":"0.2.0"}
```

### B. 注册

`POST /api/v1/auth/register`

```json
{"username":"manual_user","password":"Password123!"}
```

预期：HTTP `200`，返回 `user_id`、`username`、`roles`。

### C. 登录

`POST /api/v1/auth/login`

```json
{"username":"manual_user","password":"Password123!"}
```

保存返回的 `access_token`，后续请求使用：

```text
Authorization: Bearer <access_token>
```

### D. Agent

按顺序测试：

1. `POST /api/v1/agents`
2. `GET /api/v1/agents`
3. `GET /api/v1/agents/{agent_id}/versions`
4. `POST /api/v1/agents/{agent_id}/versions`

重点记录：状态码、返回 JSON、创建出的 `agent_id` 和版本号。

### E. Chat / Runtime

使用已创建 Agent：

1. `POST /api/v1/agents/stream`
2. `GET /api/v1/agents/sessions/{session_id}/messages`
3. `GET /api/v1/runtime/executions`
4. `GET /api/v1/runtime/executions/{execution_id}`
5. `GET /api/v1/runtime/executions/{execution_id}/events`
6. `GET /api/v1/runtime/audit-logs`

Chat 是 SSE，检查是否能收到 `start`、`delta`、`done` 事件，并记录 `request_id`、`trace_id`、`execution_id`。

### F. Tools

管理员 Token 下测试：

1. `POST /api/v1/tools`
2. `GET /api/v1/tools`
3. `POST /api/v1/tools/{tool_id}/enable`
4. `POST /api/v1/tools/{tool_id}/execute`

重点检查未授权用户、非管理员用户、工具未绑定、工具禁用等场景。

## 4. 请反馈测试结果

每个接口按下面格式反馈即可：

```text
接口：POST /api/v1/auth/login
结果：PASS / FAIL
HTTP：200
实际响应：...
问题：无 / <错误信息>
```

如果失败，请同时提供后端终端 traceback 或 Swagger 返回内容。后续直接在 `main` 分支根据实际验收结果修复并继续推进下一阶段。
