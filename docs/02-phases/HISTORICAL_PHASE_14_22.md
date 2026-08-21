# Historical Phase 14–22 — Tool Runtime / Observability / Runtime Management

> 旧连续编号历史。当前项目不使用 `Phase 14`、`Phase 15` 等连续编号作为新阶段；当前阶段只使用 `PHASE_1_x`。

## 1. Tool Runtime 14–19

### 14 — Tool Runtime 完整编排规划

定义 Registry → AgentTool Binding → Enabled → Permission → Schema → Execution Limit → HTTP Executor → Audit/Observability 的安全执行链，禁止任意 Python/Shell，要求 SSRF、timeout、response size、审计和 span。

### 15 — Tool Runtime Service

完成第一版 Service 编排骨架：Tool Registry 查询、AgentTool binding、enabled、Permission 注入点、Schema、Execution Limit、安全 HTTP Executor、Audit/Observability 注入点；当时明确 ORM Repository、RBAC、Audit/Span 持久化、Redirect 安全和完整 E2E 尚未完成。

### 16–17 — Integration / Audit

16 规划真实 SQLAlchemy Repository、RBAC、AuditLog、Tool Observability persistence、HTTP security 和 E2E。17 完成 Repository Adapter、Audit Adapter 和敏感字段脱敏，但当时仍明确未完成最终 ORM model binding、完整 RBAC、Tool Observability persistence、Redirect SSRF 和真实 DB E2E。

### 18–19 — E2E / Security

18 规划 ORM/RBAC/Observability/Redirect SSRF/PostgreSQL E2E/API。19 记录 Tool input_schema、AgentTool enabled、AuditLog 扩展、DB RBAC、Tool Runtime、HTTP/HTTPS 与 restricted IP、redirect 不自动跟随且每跳重新校验、3 次 redirect limit、`POST /api/v1/tools/{tool_id}/execute`、SQLite-backed E2E。历史修复包括构造参数位置、SQLAlchemy `metadata` 属性冲突、span key、redirect SSRF。

## 2. Observability 20–21

20 规划 Runtime Observability Query Repository、Execution detail/timeline、Tool/Model spans、Audit、owner/admin scope、分页、filters、redaction；21 记录 Execution Query Repository、DTO、RBAC、pagination/filter、Audit redaction 和查询/写入链路分离完成。

## 3. Runtime Management 22

22 规划只读 Runtime Management API + Vue：Execution list/detail/events、Audit logs、timeline、Tool/Model spans、trace/request/session filter、RBAC、pagination 和最小字段；23（旧根级文件）记录 Phase 22 完成：Runtime Query Service、Execution/Audit API、Owner/Admin scope、filter/pagination、Vue Runtime/Audit 页面、timeline、loading/empty/error、SQLite RBAC/filter tests 和 Response Contract Tests。历史记录明确 CI 未稳定，因此不把 CI 结果写成通过。

## 4. 重要边界

这些历史 Phase 与当前 Phase 1.3 的 Tool/Memory/Observability 能力存在演进关系，但不应把所有旧编号直接重新解释为当前 Phase 1.3。当前项目状态以 `PROJECT_STATUS.md` 和正式 `PHASE_1_x` 文档为准。

## 5. 来源

- `14-tool-runtime-orchestration.md`
- `15-tool-runtime-completion.md`
- `16-tool-runtime-integration.md`
- `17-tool-runtime-integration-completion.md`
- `18-tool-runtime-e2e-security.md`
- `19-tool-runtime-e2e-completion.md`
- `20-runtime-observability-governance.md`
- `21-runtime-observability-governance-completion.md`
- `22-runtime-management-api-vue-integration.md`
- `23-phase-22-completion.md`
