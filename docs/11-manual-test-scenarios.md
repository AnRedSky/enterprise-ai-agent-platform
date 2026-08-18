# 11 - 本地手动测试场景与统一测试脚本

## 1. 目的

将当前已实现的核心能力统一成可在 Windows PowerShell 本地执行的测试入口，便于每次修改后按固定场景回归并反馈结果。

测试分为两层：

1. **API 场景测试**：真实连接本地 FastAPI + PostgreSQL/Redis 等基础服务，覆盖 Health → Auth → Agents → Chat → Runtime → Tools。
2. **Backend 单元/契约回归测试**：覆盖 API、Runtime RBAC、Model Gateway、Tool Runtime、Memory、Observability 等已经存在的 pytest 测试。

## 2. 前置条件

确保后端虚拟环境已激活，并且本地 API 已启动：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
.\.venv\Scripts\Activate.ps1
```

默认 API 地址：

```text
http://127.0.0.1:8000
```

也可以通过环境变量覆盖：

```powershell
$env:API_BASE_URL = "http://127.0.0.1:8001"
```

## 3. 一键 API 场景

推荐每次代码修改后首先执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_manual_test_suite.ps1 -Mode api
```

API 场景固定顺序：

```text
Health
  ↓
Auth / register
  ↓
Auth / login
  ↓
Agents / create
  ↓
Agents / list
  ↓
Agents / versions
  ↓
Chat / stream + SSE start/done
  ↓
Runtime / executions
  ↓
Runtime / execution detail
  ↓
Runtime / execution events
  ↓
Runtime / audit logs
  ↓
Tools / list
  ↓
Tools RBAC boundary
  ↓
Tools / execute missing tool
```

脚本会自动创建测试用户和测试 Agent，不要求手工填写用户 ID、Agent ID 或 Token。

## 4. Backend 回归测试

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_manual_test_suite.ps1 -Mode unit
```

该模式统一运行当前仓库已有的核心 pytest 文件，覆盖：

- Health
- Auth
- Agents
- Chat
- Runtime API
- Runtime RBAC
- Tools API
- Tool Runtime
- Model Gateway
- Memory Context
- Memory Service
- Memory Governance
- Observability

## 5. 修改后完整回归

推荐最终执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_manual_test_suite.ps1 -Mode all
```

只有 API 场景和 pytest 回归都通过，才认为本次修改完成本地验收。

## 6. 测试结果反馈格式

执行后如果异常，请完整反馈以下内容：

```text
模式：api / unit / all
失败场景：例如 Chat / stream
HTTP：例如 500
后端日志：完整 traceback
是否修改 .env：是 / 否
```

如果通过，请直接反馈：

```text
API：PASS
Unit：PASS
```

## 7. 当前测试边界

当前统一 API 场景主要验证核心后端闭环及权限边界；Tool Runtime 文档明确指出底层 HTTP Executor 已覆盖参数 Schema、HTTP/HTTPS、受限 IP、超时和响应体限制，但 Registry 编排、权限、启用状态、调用限制、审计以及更严格 redirect/DNS rebinding 防护仍需要持续完善。因此 API PASS 不等于生产级 Tool Runtime 已全部完成。

Model Gateway 当前具备 Mock 与 OpenAI-compatible Provider 的统一抽象；真实第三方 Provider 验证需要在本地 `.env` 配置对应 Provider 后单独执行真实 Provider 验收。
