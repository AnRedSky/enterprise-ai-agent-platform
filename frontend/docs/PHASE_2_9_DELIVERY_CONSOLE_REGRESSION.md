# Phase 2.9 前端 Delivery Operations 回归修复

## 1. 基线与问题

本次修复基于远端 `main` 最新 Runtime Integration / Webhook 实现。后端已经提供 tenant-scoped `GET /webhooks/deliveries`、Delivery Audit 与 Replay Contract；Delivery 响应包含 `status`、HTTP 响应码、`last_error_code`、`last_error_message` 等可靠投递事实。

本地反馈为 `DeliveryConsole.test.ts` 首个测试失败：测试期望失败 Delivery 展示 `HTTP_ERROR`、`Replay`、`Audit`，实际反馈为“暂无 Delivery 记录”。失败发生在 2026-08-29 17:42:51 的 targeted test 中。

## 2. 根因分析

生产组件 `DeliveryConsole.vue` 已直接根据 Delivery 行数据展示 `last_error_code`，不存在静态补充错误码的设计缺陷。现有测试先等待一个组件静态存在的“失败”文本，再立即断言异步 API 数据产生的 `HTTP_ERROR`。由于“失败 / 死信”本身属于摘要标题，该等待条件并不能证明 `integrationApi.deliveries()` 已完成，也不能证明 Element Plus 表格已经完成行渲染，因此形成异步竞态。

前一次修复已经统一使用完整 `ElementPlus` 插件装配。本次进一步让 targeted test 等待真正的业务数据断言 `HTTP_ERROR`，使测试同步点与被验证的异步业务结果一致。

## 3. 设计决策

1. 不修改后端 Contract：Delivery API 已满足 UI 所需字段。
2. 不在生产 UI 增加静态 `HTTP_ERROR`：错误码必须来自真实 Delivery `last_error_code`。
3. 不修改 Replay / Audit 行为：两者继续调用后端正式 API。
4. 保留完整 `ElementPlus` 插件装配，避免 `el-table`、slot scope 等真实渲染边界被测试替身掩盖。
5. 首个回归测试等待 `HTTP_ERROR`，因为它只能在模拟 API 数据完成加载并进入表格渲染后出现；随后再验证失败状态、Replay 与 Audit 入口。

## 4. 验证范围

### Targeted

```powershell
cd frontend
npm test -- tests/views/DeliveryConsole.test.ts
```

### Full regression / production build

```powershell
cd frontend
npm test
npm run build
npm run test:gate
```

### Browser / Real API

需要本地 Backend、PostgreSQL、Redis 运行后，使用真实 JWT 登录并进入 `/integrations`，验证 Delivery 列表、状态过滤、Audit、失败 Replay，以及刷新后的持久化结果。Replay 必须只经过 Backend，不得由浏览器直接请求目标 Endpoint。

## 5. 本地事实记录

截至本次开发开始，用户反馈的 targeted test 仍为 1 failed / 1 passed。当前环境无法代替用户 Windows 本地环境执行 `npm test`、`npm run build` 或 Real API，因此不预填通过结果。最终状态必须以本地实际执行输出为准。