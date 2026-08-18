# 10 - Memory Governance 开发设计

## 1. 上一阶段

`09-memory-runtime-integration.md` 已完成 MemoryContextBuilder 与 Agent Chat Runtime 集成。Memory 已按 `user_id + agent_id + session_id` 加载并受数量/字符边界控制。当前仍缺少 CRUD、删除、生命周期和治理能力。上一阶段明确下一任务为 Memory Governance。fileciteturn115file0L2-L2

## 2. 当前目标

在进入 Observability 前，完成第一版 Memory Governance：

- Memory 创建、读取、更新、删除
- user / agent / session 数据隔离
- owner 权限校验
- Memory active 状态
- TTL / expires_at 生命周期
- 默认查询只返回未过期、active Memory
- 治理操作可被后续 AuditLog 接入
- 单元测试与集成测试基础

## 3. 设计原则

1. Memory 不是独立权限主体，访问边界继承当前用户和 Agent 上下文。
2. 任何 Memory 操作必须同时校验 `user_id` 与 `agent_id`；Session Memory 额外校验 `session_id`。
3. 删除默认采用物理删除，避免残留数据继续进入 Context。
4. 过期 Memory 不进入 Runtime Context，也不参与 Search。
5. TTL 由 `expires_at` 表示；NULL 表示不过期。
6. Memory Service 负责治理规则，API 层不得绕过 Service 直接访问数据库。
7. 本阶段不引入 Embedding、Vector DB 或自动 Memory Extraction。

## 4. 数据变更

在 `memory_records` 增加：

- `is_active`
- `expires_at`

Migration 必须作为新的 Alembic revision，不修改既有 migration。

## 5. Service 能力

```text
create / put
get
update
list_for_context
search
delete
```

所有读取操作默认过滤：

```text
is_active = true
AND (expires_at IS NULL OR expires_at > now)
```

## 6. API 规划

后续 API 使用 `/api/v1/memories`：

- `POST /memories`
- `GET /memories`
- `GET /memories/{memory_id}`
- `PATCH /memories/{memory_id}`
- `DELETE /memories/{memory_id}`

API 只能操作当前用户有权访问的 Memory。

## 7. 测试计划

至少覆盖：

- 创建
- 查询
- 更新
- 删除
- 非 owner 访问拒绝
- 不同 Agent 隔离
- Session 隔离
- 过期 Memory 不进入 Context
- inactive Memory 不进入 Context
- Search 不返回过期记录

## 8. 本任务交付物

- 本设计文档
- Memory model 更新
- Alembic migration
- MemoryService governance 能力
- API schema / route
- 测试
- 开发提交记录

## 9. 下一阶段详细计划

完成本任务后进入 `11-observability.md`：

1. 统一 execution telemetry 数据模型。
2. 记录 request / trace / execution / agent / model / tool / memory 标识。
3. 记录 latency、token usage、status、error。
4. 在 Agent Runtime 建立 execution lifecycle。
5. Model / Tool / Memory 调用形成统一 trace。
6. 增加查询接口与基础测试。

只有 Memory Governance 完成并提交后，才开始 Observability 编码。
