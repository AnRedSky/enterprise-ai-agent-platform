# Phase 23 / Task 07-B：Frontend Build 错误修复完成记录

## 1. 上一阶段

Task 07-A 已完成第三方 TypeScript 声明检查问题修复。开发人员继续执行 `npm run build` 后，错误数量已从 44 个下降到 1 个。

## 2. 本阶段实际问题

`frontend/src/views/Agents.vue` 的 Element Plus `el-table-column` 默认 slot 将 `row` 推断为 `DefaultRow`，而原实现直接将 `row` 传给 `openChat(agent: Agent)`，导致：

```text
TS2345: Argument of type 'DefaultRow' is not assignable to parameter of type 'Agent'.
```

## 3. 修复方案

不对模板 slot 强制进行类型断言，也不降低 TypeScript 严格检查。

调整 Agent 测试入口为只传递稳定的 `id`：

```text
openChat(row.id)
```

组件内部再通过 `agents` 列表查找完整 `Agent`：

```text
agents.value.find((agent) => agent.id === agentId) ?? null
```

这样模板层不再要求 Element Plus 的 `DefaultRow` 满足完整 `Agent` 结构，同时保留 `selected` 的强类型。

## 4. 变更文件

- `frontend/src/views/Agents.vue`

## 5. 验收标准

开发人员本地重新执行：

```bash
cd frontend
npm run build
```

预期退出码为 `0`，且 `vue-tsc -b` 不再出现 TS2345。

Build 通过后继续执行 `npm test`。

## 6. 提交要求

本记录与下一阶段规划文档一起提交，避免仓库代码进度与开发记录脱节。
