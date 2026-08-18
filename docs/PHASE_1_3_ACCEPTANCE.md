# Phase 1.3 功能闭环验收

> 目标：在 Windows 本地分别完成 Backend 与 Frontend 的自动化测试、API 场景和浏览器业务验收。前后端测试脚本保持独立，不把两者合并成一个测试文件。

## 1. 验收入口

### Backend

```powershell
cd backend
powershell -ExecutionPolicy Bypass -File .\scripts\run_manual_test_suite.ps1 -Mode all
```

脚本内部只负责 Backend：

- API Scenario：Health → Auth → Agents → Chat → Runtime → Tools
- Backend pytest 回归

### Frontend

```powershell
cd frontend
powershell -ExecutionPolicy Bypass -File .\scripts\run_manual_frontend_suite.ps1
```

脚本内部只负责 Frontend：

- Vitest
- Production build

## 2. Backend API 场景

`backend/scripts/run_api_scenario.ps1` 应至少验证：

1. Health
2. Register / Login
3. Agent create / list / versions
4. SSE Chat：start + delta + done
5. Runtime executions / detail / events
6. Audit logs
7. Tool list
8. 普通用户 Tool create / bind / unbind / enable / disable 必须 403
9. 缺失 Tool execute 必须 404

如果测试用户已存在，Register 返回 409 是可接受的幂等结果，随后必须继续 Login。

## 3. Backend 手工验收重点

### Agent / Version

- 创建 Agent 后能看到最新 model_id / version。
- Version 查询能看到初始版本。
- 创建新 Version 后版本号递增。
- 同一个 Agent 的 SSE Chat 必须使用当前 Version。

### Session / Message / Memory

- 第一次 Chat 返回 session_id。
- 第二次使用同一 session_id 发消息。
- GET `/api/v1/agents/sessions/{session_id}/messages` 能看到 user / assistant 消息。
- Memory context 只使用当前用户、Agent、Session 可见的数据。
- memory_limit 生效。

### Runtime / Observability

- Execution 能查询到 Chat 创建的 execution_id。
- Detail 与 Events 都能打开。
- Event 至少存在 model span。
- 成功模型调用记录 token usage（Provider 有 usage 时）。
- Execution 保存 request_id / trace_id / session_id / agent_id / agent_version / model_id。
- AuditLog 可查询并支持分页/过滤。

### Tool Runtime

- Tool 必须先注册。
- 普通用户不能执行管理员治理接口。
- disabled Tool 对普通用户不可见；管理员仍可看到并重新 Enable。
- Schema 不匹配必须失败。
- Agent 未绑定 Tool 时不能执行。
- Tool 超时必须结束，不允许无限等待。
- 成功/失败均应留下审计记录。
- 不允许任意 Python / Shell / 未授权 URL 执行。

### RBAC

至少准备普通用户 A、B 和管理员：

- A 创建 Agent A。
- B 不应看到 Agent A。
- B 使用 Agent A Chat 必须 403。
- A 的 Runtime Execution 不应泄露给 B。
- 管理员可以跨 Owner 查询 Runtime。
- A 直接访问 B 的 execution_id 应返回 404/无权访问，不能泄露对象存在性。

## 4. Frontend 浏览器验收

启动：

```powershell
cd frontend
npm run dev
```

### Login

- 未登录访问 `/dashboard`、`/agents`、`/tools`、`/runtime` 应跳转登录。
- 登录后业务 API 带 Bearer Token。
- 退出后再次访问受保护页面必须重新认证。

### Agent 工作台

- Agent 列表显示名称、模型、版本、状态。
- 创建 Agent。
- 查看 Version。
- 创建 Version。
- 调试 Chat 使用真实 SSE。
- 多轮 Chat 使用同一 session。
- Chat 完成后显示 execution_id。
- SSE/API 失败时有明确错误提示。

### Tool 工作台

管理员：

- 创建 Tool。
- Enable / Disable。
- disabled Tool 仍显示在管理列表。
- 绑定 Agent。
- 解绑 Agent。
- 执行 Tool。
- JSON 参数错误有明确提示。

普通用户：

- 可以查看允许使用的 Tool。
- 不显示管理员治理按钮。
- 直接调用治理 API 必须 403。

### Runtime

- Execution 列表。
- status 查询。
- 分页。
- 点击 Execution 打开 Timeline。
- Timeline 查询失败显示错误状态。
- 空结果显示空状态。

### Audit

- Audit Log 列表。
- status 过滤。
- 分页。
- 查询失败显示错误状态。
- 空结果显示空状态。

## 5. 自动化验收标准

Backend：

```powershell
cd backend
uv run pytest -q
```

必须 0 failed。

Frontend：

```powershell
cd frontend
npm test
npm run build
```

必须全部通过，Build 成功。

warning 不作为失败条件，但应记录并逐步清理。

## 6. 最终结论规则

- **通过**：Backend / Frontend 自动化测试通过，核心 API、RBAC、Runtime、Tool 安全边界和 Vue 核心工作台手工验收通过。
- **条件通过**：核心闭环通过，但存在已知生产化缺口，例如监控、高可用、Secret Management、正式部署。
- **不通过**：认证、RBAC/数据隔离、SSE Runtime、Execution/Observability、Tool 安全边界任一关键项失败。

Phase 1.3 验收通过不等于生产级平台全部完成；生产化能力进入后续阶段。