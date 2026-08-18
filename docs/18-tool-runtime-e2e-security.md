# 18 - Tool Runtime E2E & Security Hardening 规划

## 1. 来源

本文件是 Phase 17 完成时同步提交的下一阶段规划。按照项目规则，Phase 18 必须在开始编码前先完成文档审阅。

## 2. 目标

把 Tool Runtime 从 Repository/Audit Adapter 提升到真实数据库、RBAC、Observability、HTTP Security 和 E2E 全链路可验收状态。

## 3. 实施顺序

1. 核查现有 ORM Model 与 Migration
2. 实现 RBAC Adapter
3. 实现 Tool Observability Persistence
4. 完善 SSRF Redirect 防护
5. PostgreSQL E2E
6. Tool API
7. 测试命令稳定化与 CI smoke test 准备

## 4. 验收标准

必须覆盖：

- Tool not found
- AgentTool not bound
- Tool disabled
- RBAC denied
- Invalid schema
- SSRF blocked
- Redirect SSRF blocked
- Timeout
- Response size limit
- Execution limit
- Audit success/failure
- Observability success/failure
- PostgreSQL persistence

## 5. 安全要求

不得记录 API Key、Authorization、Cookie、Token、Secret、Password 等敏感信息；HTTP redirect 必须重新执行目标地址安全校验。

## 6. 交付要求

Phase 18 完成时提交：代码、测试、必要 Migration、`docs/19-tool-runtime-e2e-completion.md`，并同步提交下一阶段 `docs/20-...` 规划文档。
