# UI-04 AgentWorkbench 状态迁移

## 范围

本轮只迁移 `views/agents/components/AgentWorkbench.vue`，不修改其他 Agent 页面或后端 API Contract。

## 状态映射

| 区域 | Loading | Empty | Error | Permission | Success |
|---|---|---|---|---|---|
| Agent 列表 | `StatePanel.loading` | `StatePanel.empty` | `StatePanel.error + Retry` | HTTP 403 → `permission` | 有数据进入正常工作台 |
| Version Dialog | `StatePanel.loading` | 空版本使用 Empty | Error + Retry | 403 → Permission | 版本查询成功 |
| Published Version | Loading | 无生效版本 | Error + Retry | 403 → Permission | 展示生效版本 |
| Chat Context | Loading | 无可用配置 | Error + Retry | 403 → Permission | 展示调试上下文 |
| Create/Publish/Archive | 按钮 Loading | 不适用 | Error | 403 统一安全文案 | Success 状态 + 服务端刷新 |

## Chat 业务状态边界

`streaming / completed / failed / cancelled` 属于对话领域状态，不全部替换为页面级 `StatePanel`。Streaming 保留停止操作，completed/failed/cancelled 继续通过 Chat 状态条表达；上下文获取阶段使用 UI-04 页面状态。

## 权限策略

前端无法修改服务端权限模型。请求返回 403 时只展示 Permission 状态或安全提示，不暴露后端异常细节。其他失败进入 Error，并提供 Retry（可恢复场景）。

## Success 策略

创建、发布、归档、创建版本成功后先同步服务端列表，再显示 Success 状态；Toast 仅作为即时反馈，不作为数据一致性的替代。

## 兼容性

- 保留 `@/api/agents` 和 `@/api/chat` 现有调用；
- 不新增 API 字段；
- 保留 AbortController、streaming、request/trace/session/execution 标识；
- 保留 archived Agent 的业务限制；
- Design Token 用于新增/迁移后的页面样式。

## Targeted Test

`tests/views/AgentUI04.test.ts` 覆盖 Agent 列表 Loading / Empty / Error / Permission / Success，以及 Chat Context Permission。

本地执行：

```powershell
cd frontend
npm test -- tests/views/AgentUI04.test.ts
npm test -- tests/components/StatePanel.test.ts
npm run build
npm run test:gate
npm run test:final
```

本次远程代码操作未自动启动任何服务，也未手工填写测试业务数据。
