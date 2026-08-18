# 15 - Tool Runtime 完成记录与下一阶段计划

## 1. 上一阶段

完成 `14-tool-runtime-orchestration.md`，先定义 Tool Registry、Binding、Permission、Schema、Executor、Execution Limit、AuditLog 和 Observability 的完整执行链，再开始编码。

## 2. 本阶段已完成

本阶段在 `main` 完成 Tool Runtime Service 第一版：

- Tool Registry 查询入口
- AgentTool Binding 校验
- Tool enabled 校验
- Permission Checker 注入点
- Schema Validation 编排
- 单次 Execution Tool 调用次数限制
- 安全 HTTP Executor 编排
- AuditLogger 注入点
- Observability Tool Span 注入点
- Tool Runtime 单元测试

执行链：

```text
Agent Runtime
 ↓
ToolRuntimeService
 ↓
Tool / AgentTool
 ↓
Permission
 ↓
Schema
 ↓
Execution Limit
 ↓
HTTP Executor
 ↓
Audit / Observability
```

## 3. 当前边界

本阶段完成的是 Runtime Service 编排骨架。具体 ORM Repository、RBAC 策略适配、AuditLog 持久化、Tool Span 持久化和 HTTP Redirect 最终安全策略仍需要下一批集成测试确认。

因此本阶段不宣称 Tool Runtime E2E 已全部完成。

## 4. 测试

已增加 Tool Runtime Service 测试，覆盖：

- Tool disabled
- Tool 未绑定 Agent
- Permission denied
- Execution limit

完整 E2E、HTTP Executor 安全场景和 AuditLog/Observability 持久化测试待后续集成阶段完成。

## 5. 下一阶段详细计划：16 - Tool Runtime Integration & Audit

### P0-1 Repository Adapter

将 ToolRuntimeService 接入真实 SQLAlchemy Repository，使用现有 Tool / AgentTool 数据模型。

### P0-2 RBAC Adapter

接入现有用户、角色和 Agent 权限模型，禁止只依赖注入的 mock permission checker。

### P0-3 AuditLog Persistence

将 Tool 调用成功/失败写入数据库，并验证敏感字段不落库。

### P0-4 Observability Persistence

将 Tool span 与 Execution / ExecutionEvent 持久化关联。

### P0-5 HTTP Security

补充 redirect 防护、DNS rebinding 风险测试、timeout、response size limit 和受限 IP 测试。

### P0-6 E2E

覆盖真实 DB：binding、permission、schema、executor、audit、execution limit、observability。

### P0-7 API

在 Runtime Service 稳定后，再设计 Tool 管理和调试 API，避免 API 绕过治理层。

## 6. 提交要求

本次完成代码、测试、完成记录和下一阶段 `16` 规划必须全部进入 `main` 最新历史。不得提交 ZIP、日志、`.env`、缓存、构建产物或其他非项目文件。
