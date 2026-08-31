# UI-04 Dashboard 状态迁移

## 范围

本轮只迁移 `views/dashboard/components/DashboardOverview.vue`，不修改 Knowledge、Tool 或其他业务页面。

## 状态映射

| UI-04 状态 | Dashboard 语义 | 行为 |
|---|---|---|
| Loading | 四组聚合 API 尚未完成 | 使用 `StatePanel.loading`，避免空指标闪烁 |
| Empty | Agent、Tool、Execution 均为空 | 使用 `StatePanel.empty`，提示下一步 |
| Error | 非权限型聚合请求失败 | 使用 `StatePanel.error`，允许 Retry |
| Permission | 任一聚合请求返回 403 | 使用 `StatePanel.permission`，不伪装成服务异常 |
| Success | 聚合数据成功且存在平台资产 | 展示原 Dashboard 指标与工作区 |

## 设计决策

1. Dashboard 是聚合查询页面，成功态继续展示真实业务内容，不用大面积 Success 面板覆盖指标。
2. 403 单独映射 Permission；其他异常统一 Error。
3. Retry 复用原 `load()`，不改变 API Contract。
4. 保留局部 `v-loading` 与按钮 loading 作为交互级反馈；页面级状态由 `StatePanel` 管理。
5. Empty 仅在聚合数据全部为空时出现，不能把“最近执行为空”误判为整个 Dashboard Empty。

## 兼容性

不修改 `listAgents`、`listTools`、`runtimeApi.executions` 的请求参数、响应结构或路由。

## Targeted Test

`tests/views/DashboardUI04.test.ts` 覆盖 Loading / Empty / Permission / Error / Success 五类路径。

## 本地验证

```powershell
cd frontend
npm test -- tests/views/DashboardUI04.test.ts
npm test -- tests/components/StatePanel.test.ts
npm run build
npm run test:gate
npm run test:final
```

远端开发环境未执行 Node/Vitest/build，不将未执行结果标记为通过。
