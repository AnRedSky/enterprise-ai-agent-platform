# Phase 1.2 — 基础平台

## 1. 阶段目标

建立企业 Agent MVP 的基础业务闭环：身份、Agent Registry、版本、Session/Message、Runtime、Model Gateway、Tool Registry 和审计基础。

## 2. 主要范围

- User / Role / UserRole
- JWT 认证与 RBAC 基础
- Agent / AgentVersion
- Session / Message
- SSE Agent Runtime 初版
- Model Gateway 抽象、Mock Provider、OpenAI-compatible Provider 基础
- Tool / AgentTool Registry
- AuditLog
- Alembic 初始迁移
- pytest 基础测试
- Vue 3 管理端基础页面
- PostgreSQL / Redis Docker Compose

## 3. Contract / 约束

API 使用 `/api/v1`。Agent 执行关联 `request_id`、`trace_id`、`session_id`、`agent_id`、`agent_version`、`model_id`、`execution_id`。数据库结构通过 Alembic 管理；不得提交 secret、环境文件、构建产物和临时文件。

## 4. 历史记录

早期记录曾描述 feature branch / GitHub Actions；这些内容属于历史事实，不作为当前工程规则。当前工程规则以 `01-governance/DEVELOPMENT.md` 为准。

## 5. 完成定义

Phase 1.2 的基础平台能力进入 Phase 1.3 的 Model Gateway、Tool Runtime、Memory、Observability 深化阶段。