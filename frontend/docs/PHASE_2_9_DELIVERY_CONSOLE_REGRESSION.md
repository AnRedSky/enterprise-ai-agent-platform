# Phase 2.9 前端 Delivery Operations 回归修复

## 1. 基线与问题

本次修复基于远端 `main` 最新 Runtime Integration / Webhook 实现。后端已经提供 tenant-scoped `GET /webhooks/deliveries`、Delivery Audit 与 Replay Contract；Delivery 响应包含 `status`、HTTP 响应码、`last_error_code`、`last_error_message` 等可靠投递事实。

用户本地 Frontend Gate 反馈：23 个测试文件中 22 个通过，96 个测试中 95 个通过；`tests/views/DeliveryConsole.test.ts` 首个测试失败。测试期望失败 Delivery 展示 `HTTP_ERROR`、`Replay`、`Audit`，实际页面显示“暂无 Delivery 记录”。

## 2. 根因分析

生产组件 `DeliveryConsole.vue` 的表格渲染本身已经直接展示 `last_error_code`，因此当前失败不是字段缺失或 UI 条件隐藏导致。测试装配与前一次 Integrations 修复的 Element Plus 运行时边界存在同类风险：必须使用完整 Element Plus 插件进行真实组件注册，否则 `el-table` 等组件无法产生实际 slot scope，最终表现为数据虽已加载但表格行模板没有稳定渲染。

本次将回归测试统一保持为 `ElementPlus` 插件装配，并把该装配作为 DeliveryConsole 的明确测试基线；不修改生产代码来迁就测试，也不伪造 Delivery 数据源。

## 3. 设计决策

1. 不修改后端 Contract：后端 Delivery API 已满足 UI 所需字段。
2. 不在生产 UI 增加静态 `HTTP_ERROR`：必须始终来自真实 Delivery `last_error_code`。
3. 不修改 Replay / Audit 行为：两者继续调用后端正式 API。
4. 测试必须模拟 API 边界，但数据结构与生产 Contract 保持一致。
5. 失败原因必须继续显示 `last_error_code`，没有错误码时再回退 `last_error_message`。

## 4. 验证范围

### Targeted

```powershell
cd frontend
npm test -- tests/views/DeliveryConsole.test.ts
```

### Full regression

```powershell
cd frontend
npm test
npm run build
npm run test:gate
```

### Browser / Real API

需要本地 Backend、PostgreSQL、Redis 运行后，使用真实 JWT 登录并进入 `/integrations`，验证 Delivery 列表、状态过滤、Audit、失败 Replay，以及刷新后的持久化结果。Replay 必须只经过 Backend，不得由浏览器直接请求目标 Endpoint。

## 5. 本地事实记录

本文件只记录当前已经反馈的失败事实，不预填后续通过结果。最终 Gate 状态以开发者实际执行输出为准。