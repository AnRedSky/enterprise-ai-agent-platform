# 19 - Phase 18 Tool Runtime E2E & Security 完成记录

## 1. 本阶段目标

Phase 18 按 `docs/18-tool-runtime-e2e-security.md` 推进，从 Tool Runtime 编排进入真实数据库、RBAC、Audit、Observability、HTTP 安全和 E2E 验证。

## 2. 已完成

### ORM / Persistence

- Tool `input_schema` 已进入 ORM/Migration。
- AgentTool `enabled` 已进入 ORM/Migration。
- AuditLog 增加 Agent、Tool、Execution、状态、错误和 metadata 字段。
- SQLAlchemy Tool/Audit Repository 已接入。

### RBAC

- Tool Runtime 接入数据库 RBAC Adapter。
- Active/Published Agent 才允许执行。
- Agent Owner 可以执行。
- Admin Role 可以执行。
- 非授权主体被拒绝。

### Runtime

- Tool enabled 检查。
- AgentTool enabled 检查。
- Schema Validation。
- Execution Tool 调用次数限制。
- 安全 HTTP Executor。
- AuditLog 成功/失败记录。
- Tool Observability Event。

### HTTP Security

- HTTP/HTTPS scheme 限制。
- private/loopback/link-local/multicast/reserved/unspecified 地址限制。
- Redirect 不自动跟随。
- Redirect 目标重新执行安全校验。
- Redirect 次数限制为 3。
- timeout / response size limit 保持启用。

### API

已提供：

`POST /api/v1/tools/{tool_id}/execute`

API 必须通过 Tool Runtime，不允许绕过治理层直接调用 Executor。

### E2E / Tests

新增 SQLite-backed Tool Runtime E2E，验证真实 ORM + Repository + RBAC + Audit + Observability 的组合链路；新增失败审计和 Redirect SSRF 测试。

## 3. 修复记录

Phase 18 开发过程中发现并修复：

1. Runtime Service 构造参数接入错误：API 曾将 Permission/Audit 参数位置传错，已改为显式关键字参数并正确传入 Repository。
2. SQLAlchemy `metadata` 保留属性冲突：ORM Python 属性统一使用 `metadata_json`，数据库字段保持 `metadata`。
3. Tool Observability 并发 span key 使用 `tool_id` 可能互相覆盖，已改为 `(execution_id, tool_id)`。
4. HTTP Redirect 可能绕过首跳 SSRF 检查，已改为每一跳重新验证目标。

## 4. 当前边界

Phase 18 已完成代码级 E2E 覆盖，但当前仓库 CI 自动触发仍按项目临时方案保持暂停，因此不能宣称 GitHub Actions 已通过全套测试。SQLite E2E 用于快速集成验证；生产 PostgreSQL 环境的部署验证仍属于后续环境验证工作。

## 5. 下一阶段

下一阶段编号为 **20 - Runtime Observability & Governance Query**，详细计划见 `docs/20-runtime-observability-governance.md`，并与本完成记录同时作为 Phase 18 的交付文档进入 `main`。
