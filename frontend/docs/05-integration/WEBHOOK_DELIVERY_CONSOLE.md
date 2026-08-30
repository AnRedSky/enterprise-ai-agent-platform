# Phase 2.9 前端企业级集成运维控制台

## 1. 目标

本次前端改造以远端 `main` 的 Phase 2.9 后端实际 Contract 为基线，不创建前端虚拟 API。重点把已经具备的 Webhook Delivery、Audit、Replay 能力从“配置页”提升为企业级 Integration Operations Console。

后端当前已经提供：

- Destination / Subscription 租户级查询与创建；
- Durable Delivery Fact 查询；
- Delivery Audit 查询；
- Delivery Replay；
- Webhook Worker 的可靠投递、重试、死信、并发与优雅退出；
- Workflow / Agent / Scheduler 第一批 Runtime Integration Event Publisher。

因此前端职责是**观察、治理和触发正式后端动作**，而不是在浏览器复现投递逻辑。

## 2. 信息架构

Integration 页面调整为三个工作区：

```text
集成中心
├── 出站目标
│   └── Destination / Endpoint / Secret Reference / 状态
├── 事件订阅
│   └── Event Type / Destination / Priority / 状态
└── 投递运维
    ├── Delivery 状态摘要
    ├── 状态过滤
    ├── Delivery Fact 表格
    ├── Audit 时间线
    └── Failed / Dead-letter Replay
```

该结构把“配置”和“运行态治理”分离，符合企业管理后台中 Configuration / Operations 的职责边界。

## 3. API Contract 对齐

前端 `src/api/integrations.ts` 新增：

- `WebhookDelivery`
- `WebhookDeliveryAudit`
- `integrationApi.deliveries()`
- `integrationApi.deliveryAudit(deliveryId)`
- `integrationApi.replayDelivery(deliveryId)`

对应后端：

```text
GET  /webhooks/deliveries
GET  /webhooks/deliveries/{delivery_id}/audit
POST /webhooks/deliveries/{delivery_id}/replay
```

没有新增后端 Endpoint，也没有在前端实现第二套 Delivery 状态机。

## 4. UI 设计决策

### 4.1 Delivery Fact 优先

列表直接展示后端持久化事实：状态、attempt count、HTTP 状态码、最近错误、更新时间。避免使用浏览器本地计算替代后端事实。

### 4.2 Replay 必须服务端执行

Replay 按钮仅对 `failed` / `dead_letter` 状态显示。点击后调用后端 Replay API，浏览器不直接访问目标 Webhook Endpoint。

### 4.3 Audit 使用时间线

Delivery Audit 是运维人员分析失败原因的连续事实，因此采用 Timeline 展示 action、status、attempt、HTTP code、actor 和错误信息。

### 4.4 Secret 不进入前端业务状态

已有 Destination 页面只保存 `secret_ref`，不展示 Secret 明文；Delivery Console 也不读取或回显 Secret。

### 4.5 Tenant Boundary

前端不自行拼接 tenant 参数。认证 Token 与后端 `tenant_id` Contract 负责租户边界，前端只消费当前租户可见数据。

## 5. 测试策略

新增 `tests/views/DeliveryConsole.test.ts`，覆盖：

1. 失败 Delivery 正确展示错误信息、Audit、Replay 入口；
2. 点击 Audit 后按 Delivery ID 调用后端审计 API。

同时修正 `Integrations.test.ts`：使用 `ElementPlus` 插件挂载页面，避免测试环境缺少 Element Plus 组件注册导致 scoped slot 的 `scope.row` 为 `undefined`。

Frontend Gate 仍严格保持：

```powershell
cd frontend
npm test
npm run build
```

或：

```powershell
npm run test:gate
```

本次变更不调用 Backend Gate、Alembic、Real API 或 Browser E2E。

## 6. 与长期企业 UI 的衔接

本次不是一次性美化，而是建立后续企业级 UI 的统一模式：

```text
Configuration
    ↓
Runtime Fact
    ↓
Operations
    ↓
Audit
    ↓
Recovery Action
```

后续 Runtime Event Coverage 完善后，可继续把 Workflow / Agent / Scheduler 的事件事实接入统一 Operations Console，而不需要再次重做导航和交互模型。

## 7. 后续优化路线

### P0：当前阶段

- Delivery Operations Console；
- Integration 错误态、空态、加载态统一；
- Frontend API Contract 与后端 Phase 2.9-E 事件继续同步。

### P1：Runtime Integration

- Runtime Event Explorer；
- Event Type / Source / Status / Time Range 查询；
- Event → Delivery → Audit → Replay 关联链路；
- Workflow / Agent / Scheduler 事实时间线。

### P2：企业治理

- RBAC 菜单与操作权限；
- Integration 操作审计；
- Secret 管理入口与脱敏；
- Tenant / Organization Workspace 切换；
- 批量治理与危险操作二次确认。

### P3：SRE / 可观测性

- Delivery Success Rate / Retry Rate / Dead-letter Rate；
- Runtime Error Budget / Latency；
- Trace / Execution / Integration Event 关联；
- 运维告警与故障中心。

### P4：平台化

- API / Developer Console；
- Agent Asset / Marketplace；
- Evaluation / Quality；
- Cost / Quota / Billing；
- Production HA / Operations Console。
