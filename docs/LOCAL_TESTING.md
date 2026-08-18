# 本地功能测试与验收步骤

> 目标：在 Windows 本地电脑完成 Enterprise AI Agent Platform 的功能验收。本文以 `main` 分支当前实现为准。

## 1. 当前完成度评估

| 模块 | 当前状态 | 本地验收方式 |
|---|---|---|
| FastAPI 基础 API | 已实现 | `/health`、Swagger |
| JWT 注册/登录 | 已实现 | 注册、登录、Bearer 鉴权 |
| RBAC | 已实现 | 普通用户/管理员隔离测试 |
| Agent Registry / Version | 已实现 | Agent 创建、版本查询、版本创建 |
| Session / Message | 已实现 | Chat 后查询消息 |
| Model Gateway | 已实现 Mock + OpenAI-compatible | Mock Chat、真实 Provider 可选 |
| SSE Chat Runtime | 已实现 | 浏览器/PowerShell 调用 `/stream` |
| Tool Registry / Tool Runtime | 已实现基础能力 | Schema、权限、超时、审计 |
| Memory | 已实现基础能力 | Chat memory context、过期/可见性测试 |
| Observability | 已实现核心链路 | Execution / Event / Token / Error 查询 |
| Runtime / Audit 查询 | 已实现 | RBAC、过滤、分页、Timeline |
| Vue 管理端 | 已实现基础页面 | Dashboard、Agents、Runtime、Audit |
| 生产级能力 | 尚未完整 | 监控、部署、高可用、密钥管理等仍需后续阶段 |

结论：**当前不是“全部生产完成”，而是 Phase 1.3 核心能力已基本形成可运行闭环，仍需要本地手工验收以及后续生产化工作。** 开发文档规定 Phase 1.3 的顺序为 Model Gateway → Tool Runtime → Memory → Observability → Vue 管理端。fileciteturn71file0L2-L2

## 2. Windows 环境准备

### 2.1 启动 PostgreSQL 和 Redis

在项目根目录：

```powershell
docker compose up -d postgres redis
docker compose ps
```

确认 PostgreSQL、Redis 均为 `Up`/健康状态。

### 2.2 配置后端

```powershell
cd backend
uv sync
```

检查 `.env`。不要提交真实 API Key。

### 2.3 数据库迁移

```powershell
uv run alembic upgrade head
```

预期：命令正常结束，没有 migration error。

### 2.4 启动后端

```powershell
uv run uvicorn app.main:app --reload --port 8000
```

浏览器打开：

- `http://localhost:8000/health`
- `http://localhost:8000/docs`

`/health` 应返回 `status=ok`。

## 3. 自动化测试

### Backend

```powershell
cd backend
uv run pytest -q
```

验收标准：**0 failed**。DeprecationWarning 不等于测试失败，但后续应逐步清理 `datetime.utcnow()` 警告。

### Frontend

```powershell
cd frontend
npm install
npm test
npm run build
```

验收标准：测试全部通过，TypeScript/Vite build 成功。

## 4. API 手工测试

建议先用 Swagger：`http://localhost:8000/docs`。

### 4.1 注册用户

POST `/api/v1/auth/register`

```json
{
  "username": "test_user_01",
  "password": "Test12345678"
}
```

预期：HTTP 200，返回 `user_id`、`username`、`roles=["user"]`。

重复注册同名用户应返回 HTTP 409。

### 4.2 登录

POST `/api/v1/auth/login`

```json
{
  "username": "test_user_01",
  "password": "Test12345678"
}
```

预期：HTTP 200，得到 `access_token` 和 `token_type=bearer`。

在 Swagger 点击 **Authorize**，输入：

```text
Bearer <access_token>
```

### 4.3 未认证访问

GET `/api/v1/runtime/executions`

不带 Authorization。

预期：HTTP 401。

### 4.4 Agent 创建

POST `/api/v1/agents`

```json
{
  "name": "Local Test Agent",
  "description": "本地验收 Agent",
  "system_prompt": "你是一个本地测试助手。",
  "model_id": "mock-model"
}
```

预期：HTTP 200，返回 Agent ID 和 version。

然后：

GET `/api/v1/agents`

应能看到刚创建的 Agent。

### 4.5 Agent Version

GET `/api/v1/agents/{agent_id}/versions`

预期：至少存在创建 Agent 时的初始版本。

POST `/api/v1/agents/{agent_id}/versions`

```json
{
  "system_prompt": "你是第二版测试助手。",
  "model_id": "mock-model"
}
```

预期：版本号递增。

## 5. SSE Chat 验收

PowerShell 推荐使用 Python 或 curl.exe，避免 PowerShell 对 SSE 的显示差异。

```powershell
curl.exe -N -X POST "http://localhost:8000/api/v1/agents/stream" `
  -H "Authorization: Bearer <access_token>" `
  -H "Content-Type: application/json" `
  -d '{"agent_id":"<agent_id>","input":"你好，请回复一句测试成功。"}'
```

预期：连续收到 SSE `start`、多个 `delta`、`done` 事件。

重点检查 `start` 中至少包含：

- request_id
- trace_id
- session_id
- agent_id
- agent_version
- model_id

`done` 中应包含 execution_id 和 latency_ms。

## 6. Session / Message 验收

从 SSE `start`/`done` 取得 session_id，然后：

GET `/api/v1/agents/sessions/{session_id}/messages`

预期：能看到 user 和 assistant 消息，并且顺序正确。

再次使用同一个 session_id 发消息，验证历史上下文能够继续使用。

## 7. Runtime / Observability 验收

### 7.1 Execution 列表

GET `/api/v1/runtime/executions`

预期：看到刚才的 Execution。

检查：

- execution_id
- request_id
- trace_id
- session_id
- agent_id
- agent_version
- model_id
- status
- started_at
- ended_at
- duration_ms

### 7.2 Timeline

GET `/api/v1/runtime/executions/{execution_id}/events`

预期：至少存在一个 `model` Event；成功执行应有 token usage 字段。

### 7.3 Audit Log

GET `/api/v1/runtime/audit-logs`

预期：Tool 执行相关审计记录能够查询，并支持分页和过滤。

## 8. RBAC 手工验收

准备两个普通用户 A、B，以及一个管理员账号。

1. A 创建 Agent A。
2. B 登录。
3. B 查询 Agent 列表，不应看到 A 的 Agent。
4. B 使用 A 的 Agent 调用 Chat，应返回 HTTP 403。
5. A 查询自己的 Runtime Execution，可以看到自己的执行。
6. B 查询 Runtime，不应看到 A 的 Execution。
7. 管理员查询 Runtime，应能够跨 Owner 查询。
8. A 尝试直接访问 B 的 Execution ID，应得到 404/无权访问，不能泄露对象存在性。

这是核心安全验收项。

## 9. Tool Runtime 验收

使用项目已有 Tool API/测试数据验证：

1. Tool 已注册才能执行。
2. 输入不符合 Schema 时执行失败。
3. Agent 未获得 Tool 权限时执行失败。
4. 超时 Tool 不应无限等待。
5. Tool 执行成功/失败都应留下审计信息。
6. 禁止任意 Python、Shell、系统命令作为 Tool 执行。

开发约束明确禁止任意 Python、Shell 或未经授权 URL 执行。fileciteturn71file0L2-L2

## 10. Memory 验收

执行两轮 Chat：

1. 第一轮写入一个明确的上下文信息。
2. 第二轮使用同一个 session/agent 查询该信息。
3. 检查 Runtime/Memory 测试中的用户、Agent、Session 可见性边界。
4. 验证过期 memory 不再进入 context。
5. 验证 `memory_limit` 生效，不会无限扩大模型上下文。

## 11. Vue 管理端验收

启动：

```powershell
cd frontend
npm run dev
```

打开 Vite 显示的地址，逐项检查：

### Dashboard

- 页面可打开
- 无控制台致命错误

### Agents

- Agent 列表加载
- 创建 Agent
- 查看 Version
- 创建新 Version
- API 错误时页面有明确提示

### Runtime

- Execution 列表加载
- status 查询
- 分页
- 点击 Execution 打开 Timeline
- Timeline 加载失败时显示错误状态

### Audit

- Audit Log 列表
- 分页
- 过滤
- 加载失败提示

## 12. 浏览器端安全验收

打开浏览器 DevTools：

1. 未登录状态访问业务页面，应被路由/接口鉴权阻止。
2. Network 中业务请求必须带 Bearer Token。
3. Token 不应出现在 URL query string。
4. 前端错误不能把 API Key、密码或完整 JWT 写入页面日志。
5. 退出登录后再次访问受保护页面必须重新认证。

## 13. Windows WMI 异常说明

如果出现：

```text
platform.py -> _wmi_query
sqlalchemy.util.compat
```

并且 `import app.api.runtime` 长时间卡住，说明 Python/SQLAlchemy 导入期间触发了 Windows WMI 查询；这不是 Runtime Python 业务逻辑死循环。

如果：

```powershell
Get-CimInstance Win32_OperatingSystem
```

本身也卡住，则优先修复 Windows WMI 服务/权限问题，再继续判断项目问题。

不要把 WMI 卡顿误判成项目测试失败。

## 14. 最终验收记录模板

```text
测试日期：
Git commit：
Windows：
Python：
Node.js：
Docker：

[ ] docker compose postgres/redis
[ ] alembic upgrade head
[ ] /health
[ ] Swagger
[ ] 注册
[ ] 登录
[ ] 401 未认证
[ ] Agent CRUD/Version
[ ] SSE Chat
[ ] Session/Message
[ ] Execution
[ ] Timeline
[ ] AuditLog
[ ] RBAC owner isolation
[ ] Admin cross-owner
[ ] Tool schema/permission/timeout/audit
[ ] Memory visibility/expiry/limit
[ ] Vue Dashboard
[ ] Vue Agents
[ ] Vue Runtime
[ ] Vue Audit
[ ] frontend npm test
[ ] frontend npm run build
[ ] backend uv run pytest -q

发现问题：
1.
2.
3.
```

## 15. 当前验收结论规则

- **通过**：自动化测试通过 + 上述核心手工场景全部通过。
- **条件通过**：核心功能通过，但存在已知 warning/生产化缺口。
- **不通过**：认证、RBAC、数据隔离、Runtime 链路、Tool 安全边界任一项失败。

系统架构要求 Agent Runtime 作为核心执行中心，并由 Model Gateway、Tool Runtime、Memory、Observability 形成治理闭环；本次验收也按这一核心链路组织。fileciteturn74file0L2-L2
