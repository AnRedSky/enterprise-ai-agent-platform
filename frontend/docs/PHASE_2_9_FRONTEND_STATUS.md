# Frontend Phase 2.9 状态与交付边界

## 1. 当前基线

- Remote branch：`main`
- 当前远端基线：`116a46db`（Phase 2.9-E Runtime Integration 第一切片已启动）
- 前端技术栈：Vue 3 + TypeScript + Vite + Element Plus + Vitest
- Frontend Gate：`npm test` → `npm run build`

前端开发继续严格遵循 `docs/01-governance/DEVELOPMENT.md`：先对齐已稳定 Backend Contract，再进入 API Types → Vitest → UI → Frontend Gate → 联调。

## 2. 后端能力与前端覆盖

当前 Phase 2.9 后端已形成：

```text
2.9-A Event Contract                    已完成
        ↓
2.9-B Durable Event Persistence         已完成
        ↓
2.9-C Reliable Delivery                已完成 Real PostgreSQL Gate
        ↓
2.9-D Webhook Integration              实现链路完成，Real Acceptance 收口
        ↓
2.9-E Runtime Integration              第一切片完成，继续扩展
```

2.9-D 已具备 Destination、Subscription、Fan-out、Delivery Worker、SSRF/Secret Security、Delivery Audit 与 Replay；2.9-E 已开始由 Workflow / Agent / Scheduler 发布统一 Runtime Event。

## 3. 本次前端交付

### 3.1 Integration Operations Console

将 `/integrations` 从单纯配置页面升级为三个工作区：

1. 出站目标：Destination 配置；
2. 事件订阅：Event Type → Destination；
3. 投递运维：Delivery Fact、状态过滤、Audit、Replay。

新增正式组件：

```text
frontend/src/views/integrations/DeliveryConsole.vue
```

### 3.2 API Contract

`frontend/src/api/integrations.ts` 新增：

```text
GET  /webhooks/deliveries
GET  /webhooks/deliveries/{delivery_id}/audit
POST /webhooks/deliveries/{delivery_id}/replay
```

### 3.3 测试环境修复

`Integrations.test.ts` 使用 Element Plus 插件挂载真实组件，解决此前测试环境未注册 `el-table` / `el-tag` 等组件导致 scoped slot `scope.row` 为 `undefined` 的失败。

新增 Delivery Console View 测试，覆盖 Delivery 展示和 Audit 请求链路。

## 4. 关于开发者之前的测试反馈

开发者反馈中的 `Integrations.test.ts` 失败来自测试挂载环境未注册 Element Plus，同时旧工作区曾出现模板属性引号解析错误。当前远端 `main` 的 `src/views/integrations/index.vue` 已使用合法的 Vue 属性表达式语法；本次进一步把测试环境改为显式注册 Element Plus，避免同类 scoped slot 回归。

注意：该记录只描述根因和修复方案，不把未重新执行的本地命令标记为通过。

## 5. 企业级 UI 长期方向

```text
Workspace
├── Business
│   ├── Dashboard
│   ├── Agents
│   ├── Knowledge
│   └── Workflows
├── Platform
│   ├── Tools
│   ├── Model Providers
│   └── Integrations
├── Operations
│   ├── Runtime
│   ├── Integration Deliveries
│   ├── Audit
│   └── Trace / Event Explorer
└── Administration
    ├── Organization
    ├── IAM / RBAC
    ├── Secrets / Policies
    └── Usage / Quota
```

后续页面应统一遵循 Configuration → Runtime Fact → Operations → Audit → Recovery Action 的交互模型。

## 6. 下一阶段

### P0

- Runtime Event Explorer；
- Delivery / Event / Execution 关联查询；
- 统一错误、空数据、加载、权限状态；
- 完成 2.9-D Real Acceptance 对前端操作链路的覆盖。

### P1

- Workflow / Agent / Scheduler Runtime Event Coverage；
- Trace / Audit / Delivery 关联；
- Integration 与 Runtime 运维指标。

### P2

- RBAC / IAM；
- Admin Console 与 User Workspace 权限隔离；
- Secret / Policy 管理；
- Organization / Tenant 工作区。

### P3

- SRE Operations Center；
- Evaluation / Quality；
- Cost / Quota / Billing；
- API / Developer Console；
- Agent Asset / Marketplace。
