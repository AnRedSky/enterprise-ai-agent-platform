# Phase 2.9 前端 Delivery Operations 回归修复

## 1. 基线与问题

本次修复基于远端 `main` 最新 Runtime Integration / Webhook 实现。后端已经提供 tenant-scoped `GET /webhooks/deliveries`、Delivery Audit 与 Replay Contract；Delivery 响应包含 `status`、HTTP 响应码、`last_error_code`、`last_error_message` 等可靠投递事实。

本地反馈曾出现 `DeliveryConsole.test.ts` 首个测试失败：测试期望失败 Delivery 展示 `HTTP_ERROR`、`Replay`、`Audit`，实际反馈为“暂无 Delivery 记录”。失败发生在 2026-08-29 17:42:51 的 targeted test 中。

随后本地反馈显示 targeted test 已可通过，但生产构建在 `vue-tsc -b` 阶段失败：

```text
src/views/integrations/DeliveryConsole.vue:140:73 - error TS2345:
Argument of type 'DefaultRow' is not assignable to parameter of type 'WebhookDelivery'.

src/views/integrations/DeliveryConsole.vue:141:138 - error TS2345:
Argument of type 'DefaultRow' is not assignable to parameter of type 'WebhookDelivery'.
```

## 2. 根因分析

生产组件 `DeliveryConsole.vue` 的数据源明确声明为 `WebhookDelivery[]`，但 Element Plus `el-table-column` 的模板插槽 `scope.row` 在 `vue-tsc` 类型检查阶段仍按通用 `DefaultRow` 推断。Audit 与 Replay 函数此前直接要求 `WebhookDelivery`，因此业务上正确的行对象在模板类型边界处无法完成静态收窄。

该问题属于前端 UI 组件库模板类型与领域类型之间的边界适配问题，不是 Backend Contract 错误，也不是 Delivery 数据结构缺失。

## 3. 修复

在 `DeliveryConsole.vue` 增加严格的行数据类型守卫，并通过两个模板操作适配函数进入已有业务操作：

- `isWebhookDelivery(value: unknown): value is WebhookDelivery`：只检查 Audit / Replay 所需的最小业务字段。
- `openAuditRow(row: unknown)`：先完成类型收窄，再调用严格类型的 `openAudit`。
- `replayRow(row: unknown)`：先完成类型收窄，再调用严格类型的 `replay`。

模板改为调用 `openAuditRow(scope.row)` 与 `replayRow(scope.row)`，不再把 Element Plus 的 `DefaultRow` 直接传给领域函数。

## 4. 设计决策

1. 不修改 Backend Delivery Contract；当前 API 已提供完整的 Delivery 事实字段。
2. 不使用 `as WebhookDelivery` 强制类型断言绕过 `vue-tsc`，避免掩盖真实的模板行数据边界。
3. 不改变 Audit / Replay 的业务 API、权限边界或调用链。
4. 类型守卫只承担 UI 边界校验；核心业务函数继续保持 `WebhookDelivery` 强类型。
5. 无效行数据不会进入 Audit / Replay，并给出明确的用户提示。
6. 复杂边界规则使用中文 JSDoc 记录设计意图，符合项目统一代码说明规范。

## 5. 验证范围

### Targeted

```powershell
cd frontend
npm test -- tests/views/DeliveryConsole.test.ts
```

### Frontend Regression

```powershell
cd frontend
npm test
```

### Production Build

```powershell
cd frontend
npm run build
```

### Release Gate

```powershell
cd frontend
npm run test:gate
```

### Browser / Real API

需要本地 Backend、PostgreSQL、Redis 运行后，使用真实 JWT 登录并进入 `/integrations`，验证 Delivery 列表、状态过滤、Audit、失败 Replay，以及刷新后的持久化结果。Replay 必须只经过 Backend，不得由浏览器直接请求目标 Endpoint。

## 6. 当前本地事实

用户提供的最新反馈为 `npm test` 全量 23 个测试文件、96 个测试全部通过；但紧接着执行 `npm run build` 时 `vue-tsc` 报上述 2 个 `DefaultRow -> WebhookDelivery` 类型错误。因此本次修复完成后，必须重新执行 targeted test、全量 test 与 production build，最终结果以用户本地实际输出为准。本文件不预填构建通过结果。
