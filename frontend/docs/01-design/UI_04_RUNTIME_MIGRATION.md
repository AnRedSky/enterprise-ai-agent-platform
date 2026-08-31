# UI-04 Runtime 页面状态迁移记录

## 范围

本轮只迁移 Runtime 工作台的 `RuntimeObservabilityOverview`，不修改 Execution、Correlation、Diagnostics 等其他 Runtime 子页面。

## 状态映射

| 状态 | 触发条件 | UI |
|---|---|---|
| Loading | `runtimeApi.executions` 请求进行中 | `StatePanel(loading)` |
| Empty | 请求成功且返回 0 条 Execution | `StatePanel(empty)` |
| Error | 请求失败且 HTTP 状态不是 403 | `StatePanel(error)` + 重试 |
| Permission | HTTP 403 | `StatePanel(permission)` |
| Success | 请求成功且存在 Execution | 保持原指标与诊断入口 |

## 设计决策

1. 保留原有 `loading`、`error` 和 Execution 数据计算逻辑，不修改 Runtime API Contract。
2. 403 从通用 Error 中独立出来，避免把权限问题误报为系统故障。
3. Empty 只在请求成功且数据为空时出现；网络失败不能显示 Empty。
4. Error 提供 Retry，Retry 会重新发起原请求并重置错误状态。
5. Success 不使用额外成功 Toast，而是继续展示真实运行指标；数据来自服务端响应。
6. 保留原有状态筛选入口，点击指标仍进入 `/runtime` 并携带对应状态。
7. 页面私有颜色、边框和阴影迁移到 Design Tokens。

## 测试

新增 `tests/views/RuntimeUI04.test.ts`，覆盖 Loading → Success、Empty、Error、Permission。

## 本地验证

```powershell
cd frontend
npm test -- tests/views/RuntimeUI04.test.ts
npm test -- tests/components/StatePanel.test.ts
npm run build
npm run test:gate
npm run test:final
```

当前远端开发环境没有实际运行本地 Node/Vitest/build，因此测试结果必须以本地执行结果为准。
