# UI-04 Audit Log 页面状态迁移记录

## 范围

本轮只处理 `AuditLogPanel.vue`，不修改 Runtime、Workflow、Agent 或其他治理页面。

## 状态映射

| 状态 | 触发条件 | UI |
|---|---|---|
| Loading | `runtimeApi.auditLogs` 请求进行中且暂无旧数据 | `StatePanel(loading)` |
| Empty | 请求成功且 `items.length === 0` | `StatePanel(empty)` |
| Error | 请求失败且不是 403 | `StatePanel(error)` + 重试 |
| Permission | HTTP 403 | `StatePanel(permission)` |
| Success | 查询成功并得到记录 | 保留表格，并显示同步成功反馈 |

## 设计决策

1. 不改变 `runtimeApi.auditLogs` Contract、分页参数或筛选参数。
2. 403 独立为 Permission，避免把权限不足误判为系统故障。
3. Empty 只表示成功响应为空，不能由请求异常触发。
4. Loading 与已有数据分离：刷新已有记录时继续允许表格使用 `v-loading`，避免页面闪烁。
5. Error 的 Retry 重新执行当前页、当前 pageSize 和 status 筛选。
6. Success 仅表达本次服务端同步完成，不改变审计记录业务状态。
7. 页面容器和响应式样式改用 Design Tokens，保留原 Execution 深链。

## 测试

新增 `tests/views/AuditLogUI04.test.ts`，覆盖 Loading、Success、Empty、Error、Permission。

## 本地验证

```powershell
cd frontend
npm test -- tests/views/AuditLogUI04.test.ts
npm test -- tests/components/StatePanel.test.ts
npm run build
npm run test:gate
npm run test:final
```

远端开发环境未实际运行 Node/Vitest/build；测试结果必须以本地执行结果为准。
