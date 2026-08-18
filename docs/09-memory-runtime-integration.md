# 09 - Memory Runtime Integration

## 1. 上一阶段

完成项目开发规划、CI 临时暂停和 `main` 基线切换；Memory 已具备数据模型、Migration 和 MemoryService。

## 2. 当前目标

把 Memory 从独立 Service 接入 Agent Chat Runtime，使每次 Agent 执行能够按 user + agent + session 加载受控 Memory，并注入模型上下文。

## 3. 当前完成

- 新增 `MemoryContextBuilder`。
- Chat Runtime 自动加载 MemoryService.list_for_context。
- Memory 作为独立 system context 注入模型。
- Memory 数量限制由 API 请求参数 `memory_limit` 控制，范围 1-50。
- Memory Context 默认字符上限 6000。
- SSE `start` 事件增加 `memory_count`。
- 新增 Memory Context 单元测试。

## 4. Context 顺序

```text
System Prompt
    ↓
Memory Context
    ↓
Session History
    ↓
Current User Input
```

Memory 明确标识为参考信息，不能覆盖系统指令。

## 5. 数据隔离

Memory 查询同时使用：

- `user_id`
- `agent_id`
- `session_id`

Session Memory 与长期 Memory 的读取边界由 MemoryService 控制。

## 6. 当前限制

- 当前 Memory 检索仍是 PostgreSQL / ILIKE。
- 尚未实现 Embedding / Vector DB。
- 尚未实现自动 Memory Extraction。
- 尚未实现 Memory TTL / 删除 / Governance API。
- 当前 Chat 仍使用 MockProvider，真实模型接入仍需后续完善。

## 7. 测试

增加 `backend/tests/test_memory_context.py`，覆盖空 Memory 与上下文边界。

CI 当前处于临时暂停自动触发状态，测试结果以本地 / 手动 workflow 验证为准。

## 8. 下一步

进入 `10-memory-governance.md`：补充 Memory CRUD、删除、权限、生命周期和更完整的集成测试；之后再进入 Observability。
