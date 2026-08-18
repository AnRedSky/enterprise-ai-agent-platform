# API 场景一键测试

用于本地手动验收后端核心 API，执行顺序固定为：

**Health → Auth → Agents → Chat → Runtime → Tools**

脚本位置：`backend/scripts/run_api_scenario.ps1`

## 1. 前置条件

确认后端服务已经启动，例如：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

如果项目使用 `.env` 修改了端口，可以通过参数覆盖：

```powershell
$env:API_BASE_URL = "http://127.0.0.1:8080"
```

也可以直接传参：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_api_scenario.ps1 -BaseUrl "http://127.0.0.1:8080"
```

## 2. 一键执行

在 `backend` 目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_api_scenario.ps1
```

脚本会自动：

1. 检查 `/health`。
2. 创建唯一测试用户并登录，取得 Bearer Token。
3. 创建测试 Agent，并验证 Agent 列表、版本接口。
4. 调用 Chat SSE，检查 `start` / `done` 生命周期事件。
5. 查询 Runtime executions，并在有执行记录时检查详情和 events，同时检查 audit logs。
6. 查询 Tools，并用不存在的 Tool ID 验证受保护的错误响应（404/403）。

## 3. 指定测试账号

默认每次运行都会生成唯一用户名。如果希望重复使用已有账号：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_api_scenario.ps1 `
  -Username "scenario_user" `
  -Password "TestPassword123!"
```

账号必须已经存在且密码正确；如果不存在，建议不要指定 `-Username`，让脚本自动注册。

## 4. 成功标准

最后看到：

```text
[PASS] API scenario completed: Health -> Auth -> Agents -> Chat -> Runtime -> Tools
```

即表示本次场景测试通过。

每一步都会输出 `[RUN]`、`[ OK ]` 或 `[FAIL]`，失败时脚本立即退出，便于定位具体接口。

## 5. 注意事项

- Chat 使用项目当前的 `mock-model`，不会依赖外部模型 API Key。
- 场景测试会在数据库中创建测试用户、Agent、Session/Message 和 Runtime 相关记录；建议使用专用测试数据库。
- Tools 的创建接口要求 admin，因此普通测试用户只执行 Tools 查询和“未知 Tool”错误路径，不会修改 Tool 配置。
- 如果 PowerShell 禁止执行脚本，请仅对当前命令使用 `-ExecutionPolicy Bypass`，不要修改系统全局执行策略。
