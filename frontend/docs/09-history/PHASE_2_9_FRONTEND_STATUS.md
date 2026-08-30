# Frontend Phase 2.9 状态与交付边界

## 1. 当前基线

- Remote branch：`main`
- 当前远端基线：`109b9d203a635221635a0f86ee9da03cac95d2e3`
- 前端技术栈：Vue 3 + TypeScript + Vite + Element Plus + Vitest
- Backend 当前阶段：Phase 2.9-E Runtime Integration 第三切片
- Frontend Gate：`npm test` → `npm run build`

前端开发继续严格遵循 `docs/01-governance/DEVELOPMENT.md`：先对齐已稳定 Backend Contract，再进入 API Types → Vitest → UI → Frontend Gate → 联调。

## 2. 后端能力与前端覆盖

当前 Backend 已形成：

```text
2.9-A Event Contract                    已完成
        ↓
2.9-B Durable Event Persistence         已完成
        ↓
2.9-C Reliable Delivery                已完成 Real PostgreSQL Gate
        ↓
2.9-D Webhook Integration              实现链路完成，Real Acceptance 收口
        ↓
2.9-E Runtime Integration              第三切片开发中
```

2.9-D 已具备 Destination、Subscription、Fan-out、Delivery Worker、SSRF/Secret Security、Delivery Audit 与 Replay；2.9-E 当前已经覆盖 Workflow Governance、Agent Tool、Knowledge Retrieval、Model Provider helper 以及 Scheduler 事件模型，下一切片继续推进 Scheduler transaction wiring、tenant-scoped Event Operations 与 Real Acceptance。

## 3. 本次前端交付

### 3.1 Integration Operations Console

`/integrations` 保持三个工作区：

1. 出站目标：Destination 配置；
2. 事件订阅：Event Type → Destination；
3. 投递运维：Delivery Fact、状态过滤、Audit、Replay。

本次 UI 优化进一步：

- 将指标卡调整为“出站目标 / 事件订阅 / 唯一事件类型”；
- 统一表格时间显示；
- 无 Destination 时给出明确创建引导；
- 安全提示明确 Replay 只经过 Backend，不在浏览器直连 Endpoint；
- Event Type 示例与当前 Workflow Integration Contract 对齐。

### 3.2 测试环境修复

最新本地反馈仍显示 `Integrations.test.ts` 两个测试失败，并伴随 Element Plus 组件未解析警告。此前仅安装 `ElementPlus` 插件不足以在当前测试运行时稳定建立组件解析边界，因此本次测试改为显式注册 Integrations 页面实际使用的 Element Plus components，并为 `v-loading` 提供测试 directive。

测试新增一个 `mountIntegrations()` 装配入口，避免多个测试复制挂载配置。

### 3.3 自动化测试入口

```powershell
cd frontend
npm test
npm run build
npm run test:gate
```

`test:gate` 必须保持 Frontend 独立，只执行 Vitest → production build，不调用 Backend pytest、Alembic 或 Real API。

## 4. 本次测试结论

用户反馈的基线结果为：22 个测试文件中 21 个通过、1 个失败；94 个测试中 92 个通过、2 个失败，因此 Frontend Gate 为阻塞状态。

本次代码已针对失败根因完成修复，但当前环境无法直接执行用户 Windows 本地命令，因此在没有新的实际执行结果前，不将 Gate 标记为通过。

## 5. 手动验收流程

1. 启动 Backend，并确保 PostgreSQL / Redis 本地环境正常。
2. `cd frontend && npm run dev`。
3. 登录后进入“集成中心”。
4. 验证 Destination：创建、刷新、启用状态、Secret 引用状态、更新时间。
5. 验证 Subscription：无 Destination 时禁用并显示引导；有 Destination 后可创建；Event Type 与 Destination 映射正确。
6. 验证 Delivery Operations：状态过滤、Audit、失败 Replay。
7. Replay 必须通过 Backend API，不得从浏览器直接访问目标 Webhook Endpoint。
8. 刷新页面确认真实持久化结果能够重新加载。
9. 再执行 Frontend Gate；若范围涉及真实后端联调，再独立执行 Real API / Browser E2E Gate。

## 6. 企业级 UI 长期方向

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

后续统一遵循 Configuration → Runtime Fact → Operations → Audit → Recovery Action 的产品交互模型。

### P0

- 收口 Frontend Gate；
- Runtime Event Explorer；
- Delivery / Event / Execution 关联查询；
- 统一 Loading / Empty / Error / Permission 状态。

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
