# Frontend UI 完整性 Gap Audit 与 P0/P1 补齐计划

> 状态：主线开发收口，Gap Audit 已无已知代码级阻塞项  
> 基线：`frontend` 已同步最新 `main`  目标：以 Backend Contract 为事实源，逐页补齐 UI-03/UI-04/UI-05，并在全部开发完成后统一执行验证。

## 1. 审计维度

每个页面检查：

1. UI-03：PageHeader / PageToolbar / SurfaceCard / MetricCard 等公共模式。
2. UI-04：Loading / Empty / Error / Permission / Success 五态。
3. UI-05：Form / Dialog / Drawer / Confirm / Action / Refresh 闭环。
4. Durable Fact：实体关系必须由后端返回的 durable ID 驱动，不通过数组顺序、时间、字符串或分页位置推断。
5. Deep Link：URL 使用真实 ID，刷新后可恢复准确上下文。
6. Permission：403 使用统一 Permission 状态，不显示伪造的可操作入口。
7. Contract：只调用已确认的 Backend API，不新增推测接口。
8. Test：关键路径必须有 targeted test；当前阶段只准备脚本，不执行。

## 2. 页面台账

| 优先级 | 页面 | UI-03 | UI-04 | UI-05 | 状态 |
|---|---|---|---|---|---|
| P0 | Runtime | 已建立 | 核心已建立 | 持续补齐 | 待正式验证 |
| P0 | Workflow Lifecycle | 已建立 | 已建立 | canonical reference | 待正式验证 |
| P0 | Workflows | 已建立 | 已补齐 | 已补齐 | 待正式验证 |
| P0 | Agents | 已建立 | Debug 已收敛 | 已补关键防护 | 待正式验证 |
| P1 | Knowledge | 已建立 | 已有 | 第一轮完成 | 待正式验证 |
| P1 | Tools | 已建立 | 已有 | 第一轮完成 | 待正式验证 |
| P1 | Organizations | 已补齐 | 已补齐 | 已补齐 | 待正式验证 |
| P1 | Model Providers | 已补齐 | 已补齐 | 已补齐 | 待正式验证 |
| P1 | Integrations | 已补齐 | 已补齐 | 已有真实创建闭环 | 待正式验证 |
| P1 | Operations Console | 已建立 | 已收敛 | 已收敛 | 本轮收口完成 |
| P1 | Audit | 已建立 | 已收敛 | 只读查询闭环 | 本轮收口完成 |
| P1 | Dashboard | 已建立 | 已收敛 | 以导航为主 | 本轮收口完成 |
| P1 | Workflow Triggers | 已迁移共享状态与 SurfaceCard | 已补齐页面/Trigger/Scheduler 五态子集 | 已补齐按实体 ID 的 action loading、确认与 Backend refresh | 本轮收口 |
| P2 | Runtime Correlations | 已迁移 SurfaceCard | 已统一 Loading / Empty / Error | 只读关联与 durable deep-link 已保留 | 本轮收口 |

## 3. 已完成的代码主线

### P0-01 Workflows

已迁移公共页面模式，并补齐 Version 状态、Execution/Audit stale-data 清理、Trace loading/重复查询保护、Create/Edit/Delete/Create Version/Publish 操作保护、Archived read-only 与确认框。

Targeted：`frontend/tests/views/WorkflowsUI03.test.ts`、`frontend/tests/views/WorkflowsUI04UI05.test.ts`。  
状态：**未执行**。

### P0-02 Runtime

Execution 深链使用真实 `execution_id`；目标不在当前分页时通过 durable ID 直接加载；关系导航使用后端 `workflow_id` 与 execution ID。

Targeted：`frontend/tests/views/RuntimeDeepLinkRecovery.test.ts`。  
状态：**未执行**。

### P0-03 Agents

Agent Workbench 已移除 `listVersions(agent.id)[0]` 形式的“最新版本”推断；发布必须明确选择 `version.id`，并补齐 Archive/Create/Create Version/Publish 操作保护。

Targeted：`frontend/tests/views/AgentWorkbenchUI05.test.ts`、`frontend/tests/views/AgentDebugExperienceUI04.test.ts`。  
状态：**未执行**。

### P1-01 Knowledge

Knowledge Base → Document → Version → Chunk 均通过真实 ID 关联；检索保留后端返回的 `document_id`、`document_version_id`、`chunk_id` 等事实。

Targeted：`frontend/tests/views/KnowledgeWorkbenchUI03UI05.test.ts`。  
状态：**未执行**。

### P1-02 Tools

Tools 已统一公共 UI 模式，启停、绑定/解绑、执行均使用明确 tool/agent ID；危险状态变更使用确认并在成功后刷新 Backend facts。

Targeted：`frontend/tests/views/ToolWorkbenchUI03UI05.test.ts`。  
状态：**未执行**。

### P1-03 Organizations

组织列表与详情已迁移 `PageHeader` / `SurfaceCard` / `StatePanel`；补齐 Loading / Empty / Error / Permission、创建/成员变更/删除/所有权转移等操作保护；成员操作使用 durable membership/user/organization ID。

Targeted：`frontend/tests/views/OrganizationsUI03UI05.test.ts`、`frontend/tests/views/OrganizationDetailUI05.test.ts`。  
状态：**未执行**。

### P1-04-A Model Providers

`organizations/model-providers.vue` 已完成第一轮 Gap Audit 与迁移：

- 使用 `PageHeader`、`SurfaceCard`、`StatePanel`、`ConfirmDialog`；
- 页面级 Loading / Empty / Error / Permission / Success 完整；
- provider 的 profile 列表独立维护 Loading / Empty / Error / Permission，避免 stale data；
- provider/profile 创建与编辑有独立 saving 状态，阻止重复提交；
- 删除 provider/profile 使用确认闭环，成功后以 Backend refresh 为准；
- provider → profile 关系只使用 `provider.id` / `profile.provider_id`，更新/删除只使用实体自身 `id`；
- 不展示或重新提交 secret 正文，只保留 `credential_ref` 引用。

Targeted：`frontend/tests/views/ModelProvidersUI03UI05.test.ts`。  
状态：**未执行**。

### P1-05-A Integrations

`integrations/index.vue` 已完成第一轮 Gap Audit 与公共模式迁移：

- 使用 `PageHeader`、`MetricCard`、`StatePanel`、`SurfaceCard`；
- 页面级 Loading / Empty / Error / Permission / Success 完整；
- 投递目标与事件订阅空状态使用 `StatePanel`；
- 修复原页面通过 `destinations[0]` 自动选择订阅目标的关系推断，创建订阅必须显式选择 `destination_id`；
- 创建投递目标/事件订阅增加独立 saving 状态和重复提交保护；
- 创建成功后重新读取 Backend facts，失败不关闭对话框；
- 继续使用已确认的 `/webhooks/destinations`、`/webhooks/subscriptions`、`/webhooks/deliveries`、`/runtime/integration-events` Contract；
- secret 只展示 `secret_ref`/配置状态，不读取或展示 secret 明文；
- Delivery replay 等现有子工作台继续使用后端 durable delivery ID，不由本页新增推测写接口。

Targeted：`frontend/tests/views/IntegrationsUI03UI05.test.ts`。  
状态：**未执行**。

### P1-06-A Operations Console

实际路由为 `/runtime/operations`，页面主体为 `integrations/OperationsConsole.vue`；Backend Contract 已确认覆盖 Runtime Overview、Global Posture、Alert、Provider、Metrics、Runtime Audit、Dead Letter replay 等既有子工作台。

本轮已完成内部统一收口：

- 页面壳层与内部子工作台统一使用 `PageHeader` / `PageToolbar` / `MetricCard` / `SurfaceCard` / `StatePanel`；
- 各独立查询域维护自己的 Loading / Empty / Error / Permission 语义；
- reload 失败清空受影响的旧数据，避免 stale-data；
- Provider / Alert / Dead Letter 等 mutation 使用实体 durable ID、action loading、duplicate-submit protection；
- mutation 成功后重新读取 Backend facts，不使用本地 optimistic rollback 作为最终状态；
- Provider / Alert Rule 开关使用 `:model-value` + change event，不通过 `v-model` 直接写入后端事实对象；
- 高影响操作使用确认闭环；
- Operations → Runtime / Audit → Runtime 保留真实 `execution_id` / `workflow_execution_id` / `audit_id` / `delivery.id`；
- Runtime correlation 仅依据 Backend 返回的 durable correlation facts，不按列表位置推断。

Targeted：`frontend/tests/views/OperationsConsoleUI03.test.ts`、`frontend/tests/views/OperationsRuntimeCorrelation.test.ts`、`frontend/tests/views/FullSiteConsistencyStaticAudit.test.ts`。  
状态：**未执行**。

### P1-07-A Audit

`/runtime/audit` 已完成内部一致性收口：

- `AuditLogWorkbench.vue` 使用统一 `PageHeader`；
- `AuditLogPanel.vue` 内部统一使用 `PageToolbar` / `SurfaceCard` / `StatePanel`；
- 移除 `v-loading` / 自定义空态，Loading / Permission / Error / Empty 统一由 `StatePanel` 表达；
- 保留状态筛选与分页，查询按钮具备 loading 防重复提交；
- 查询失败主动清空 `items` / `total`，不保留 stale audit data；
- Audit 记录的 Execution 导航只使用后端返回的 `execution_id`，构造 `/runtime?execution_id=<real-id>&source=audit`；
- Audit 本身保持只读，不新增未经确认的 mutation API；
- unknown action/status 保留可诊断信息，不静默伪装成正常状态。

Targeted：`frontend/tests/views/AuditLogUI03Correlation.test.ts`、`frontend/tests/views/AuditDashboardConsistency.test.ts`。  
状态：**未执行**。

### P1-08-A Dashboard

Dashboard 已完成一致性收口：

- 保持 `PageHeader` / `MetricCard` / `SurfaceCard` / `StatePanel`；
- 移除 `v-loading` 与 raw `el-empty`；最近执行空态统一使用 `StatePanel`；
- 聚合查询失败时主动清空指标与最近执行数据，避免 stale dashboard facts；
- 最近 Execution 继续使用后端返回的 `execution_id` 构造 `/runtime?execution_id=<real-id>&source=dashboard`；
- 不根据数组首项、时间或分页位置推断目标执行；
- Dashboard 保持导航职责，不新增未经确认的写操作。

Targeted：`frontend/tests/views/DashboardConsistency.test.ts`、`frontend/tests/views/AuditDashboardConsistency.test.ts`。  
状态：**未执行**。

### P2 Runtime Correlations

`runtime/components/RuntimeCorrelations.vue` 本轮完成最后一个已发现的旧 UI primitive 遗留收口：

- `el-card` 全部迁移为 `SurfaceCard`，保留原有 header slot、表格、分页和 durable fact 展示；
- 页面 Loading / Error / 初始 Empty 使用 `StatePanel`；
- Execution 缺失、Trace/Audit 无记录、Operator Action 无记录均使用 `StatePanel`，不再使用 raw `el-empty`；
- 查询失败清空 `result`，避免继续展示旧关联事实；
- Execution、Trace、Audit、Workflow navigation 继续使用后端返回的 `execution.id`、`trace_id`、`audit.id`、`workflow_execution_id`；
- 未新增任何推测 API 或数组位置关系。

Targeted：`frontend/tests/views/RuntimeCorrelationsUI03UI04.test.ts`。  
状态：**未执行**。

### Full-site consistency closeout

已建立全站静态一致性审计脚本：

`frontend/tests/views/FullSiteConsistencyStaticAudit.test.ts`

覆盖：

- raw `el-card` / `v-loading` / `el-empty` / `el-result`；
- `[0]` 数组位置实体推断；
- `sort/reverse` 列表顺序关系推断；
- optimistic boolean/status mutation；
- Operations Console Provider / Alert Rule switch 必须使用 `:model-value` + change event，禁止 `v-model="row.enabled"` 与本地 `Object.assign(row, ...)`；
- Workflow Trigger action guard / Backend refresh；
- 核心 P0/P1 页面共享 UI primitive；
- Operations / Audit / Dashboard / Trigger durable deep-link。

另有：

`frontend/tests/views/FullSiteConsistencyGapAudit.test.ts`

用于核心页面 inventory、durable ID、Runtime correlation 回归检查。

Targeted：以上脚本均**未执行**。

**当前代码级 Gap Audit 结论：0 个已知阻塞项。** 这表示主线开发项已完成收口，不等同于测试已通过；所有测试仍保持未执行。

## 4. Contract 与安全原则

- 前端只能调用已经存在并确认的 Backend API。
- 成功后的持久化状态以 Backend refresh 为准，不本地伪造。
- Webhook secret 不回显、不读取旧 secret、不在未修改时重新提交。
- Scheduler 在完整 HTTP Contract、状态机、lease、misfire、audit/trace 关联确认前保持只读。
- Unknown enum/status 必须保留可诊断信息，不能静默映射成正常状态。

## 5. Definition of Done

页面只有同时满足以下条件才可标记“已完成”：

- [ ] UI-03 完成
- [ ] UI-04 五态完整
- [ ] UI-05 关键操作闭环完成
- [ ] Backend Contract 已确认
- [ ] 无关系推断
- [ ] Deep Link 使用 durable ID
- [ ] targeted tests 实际通过
- [ ] `npm run test:unit` 通过
- [ ] `npm run build` 通过
- [ ] 文档同步
- [ ] 原子提交

## 6. 分阶段测试策略

当前策略：**主线开发与 Gap Audit 已完成，下一阶段切换正式测试；在测试执行前不得将任何 targeted/full-unit/build/gate 标记为通过。**

当前所有测试记录必须使用：

- Targeted result：**未执行**
- Full unit：**未执行**
- Build：**未执行**
- Gate：**未执行**
