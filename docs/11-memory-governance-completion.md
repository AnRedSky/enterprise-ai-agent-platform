# 11 - Memory Governance 阶段提交与下一阶段计划

## 1. 上一阶段

`10-memory-governance.md` 先行定义了 Memory CRUD、数据隔离、active 状态、TTL、过期过滤和测试要求；本次严格按照“文档先行，再开发”的顺序实施。fileciteturn115file0L2-L2

## 2. 当前完成

- `memory_records` 增加 `is_active`、`expires_at`。
- 新增 `0003_memory_governance` Alembic revision。
- MemoryService 增加 get / update / delete。
- Context 与 Search 默认过滤 inactive / expired Memory。
- `put` 支持 `expires_at`。
- 增加 Memory Governance 测试。

## 3. 当前边界

本次未宣称完整 HTTP CRUD API 已完成；API 层需要基于现有项目 API 结构单独设计、测试和提交。当前交付重点是数据层与 Service 层治理能力，避免绕过现有认证/RBAC 体系直接暴露接口。

## 4. Git 提交

本阶段按功能拆分提交：

- `docs: define memory governance before implementation`
- `feat: add memory governance migration`
- `feat: add memory governance fields`
- `feat: add memory governance service`
- `test: add memory governance coverage`

## 5. 下一阶段：Observability 文档先行

下一任务必须先完成 `12-observability.md`，文档确认后再编码。

详细实施顺序：

1. 定义 `Execution` / `ModelCall` / `ToolCall` / `MemoryAccess` telemetry 数据结构。
2. 统一 `request_id`、`trace_id`、`execution_id`、`session_id`、`agent_id`、`agent_version`、`model_id`、`tool_id`。
3. 建立 Agent Runtime execution lifecycle：started → running → completed / failed。
4. 记录 latency、token usage、status、error。
5. Model / Tool / Memory 调用挂载到同一 execution trace。
6. 增加持久化 Migration 与查询 Service。
7. 增加测试。
8. 最后记录 `13-observability-completion.md`，再决定下一模块。

## 6. 验收原则

CI 自动触发目前仍处于暂停状态；不得以“CI 绿灯”作为本阶段已通过的依据。每次提交必须核查 GitHub 上的 commit 是否存在，并记录实际可验证结果；任何无法验证的信息必须明确标记为“未验证”。
