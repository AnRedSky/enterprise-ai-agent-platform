# 06 - Phase 1.3 Memory 开发记录

## 1. 上一阶段

Tool Runtime 已完成第一批安全执行基础，包括参数 Schema 校验、HTTP Executor、基础 SSRF 网络地址防护、超时与响应大小限制；同时建立了 Tool Runtime 设计和验收记录。

## 2. 历史文档补录

本次同时补录了项目早期开发记录：

- `01-project-initialization.md`
- `02-phase-1.2-foundation.md`
- `03-phase-1.3-model-gateway.md`

这些文档用于恢复从技术选型、Phase 1.2 到 Model Gateway 的可追溯开发历史。

## 3. Memory 目标

根据当前项目分层，Memory 位于 Agent Runtime 与持久化层之间。本阶段先实现 PostgreSQL 基础 Memory，不引入向量数据库或自动记忆提取，避免在基础能力尚未稳定时增加复杂度。

## 4. 当前实现

新增 `MemoryRecord`：

- user_id
- agent_id
- session_id（可选）
- memory_type
- memory_key
- content
- created_at
- updated_at

新增 `MemoryService`：

- `put()`：保存长期记忆记录
- `list_for_context()`：按用户、Agent、Session 获取上下文记忆
- `search()`：基于 PostgreSQL 文本匹配检索记忆

新增 Alembic `0002_memory` 迁移。

## 5. Context 规则

Session 级查询优先匹配当前 Session，同时允许读取没有 Session 绑定的 Agent/User 长期记忆。默认限制上下文记忆数量，避免一次执行无限扩大 Prompt。

## 6. 当前边界

本阶段不做：

- 向量数据库
- embedding
- 自动摘要
- LLM 自动写入长期记忆
- 跨租户共享记忆
- 无权限的用户记忆访问

这些能力需要在后续 Memory 治理和 Observability 完成后再逐步引入。

## 7. 测试

已增加 MemoryService 基础测试，覆盖写入和上下文数量限制。

## 8. 下一步

下一任务为 `07-memory-runtime-integration.md`：将 MemoryService 接入 Agent Runtime 的 Context Builder，并补充 Session/Memory 集成测试；之后进入 Observability。
