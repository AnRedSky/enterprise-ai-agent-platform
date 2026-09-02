# Frontend UI 完整性 Gap Audit 与 P0/P1 补齐计划

> 状态：执行中  
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
| P0 | Runtime | 已建立 | 核心已建立 | 持续补齐 | 待验证 |
| P0 | Workflow Lifecycle | 已建立 | 已建立 | canonical reference | 待验证 |
| P0 | Workflows | 已建立 | 已补齐 | 已补齐 | 待验证 |
| P0 | Agents | 已建立 | Debug 已收敛 | 已补关键防护 | 待验证 |
| P1 | Knowledge | 已建立 | 已有 | 第一轮完成 | 待验证 |
| P1 | Tools | 已建立 | 已有 | 第一轮完成 | 待验证 |
| P1 | Organizations | 已补齐 | 已补齐 | 已补齐 | 待验证 |
| P1 | Model Providers | 已补齐 | 已补齐 | 已补齐 | 待验证 |
| P1 | Integrations | 已补齐 | 已补齐 | 已有真实创建闭环 | 待验证 |
| P1 | Operations Console | 第一轮建立统一 PageHeader Shell | 子工作台待统一 | 现有真实操作待收敛 | 开发中 |
| P1 | Audit | 第一轮建立统一 PageHeader Shell | 已有五态 | 读操作为主 | 开发中 |
| P1 | Dashboard | 已建立 | 已建立 | 以导航为主 | 开发中 |

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

本轮完成第一层公共 UI 壳层迁移：

- 新增 `OperationsConsoleWorkbench.vue`，使用统一 `PageHeader`；
- `/runtime/operations` 改由共享页面壳层承载，保留既有子工作台与真实 API；
- 保留窗口范围、刷新和现有运维操作，不改变 Backend Contract；
- 不引入推测 API，不改变 Provider/Alert/Delivery durable ID；
- Targeted：`frontend/tests/views/OperationsConsoleUI03.test.ts`，**未执行**。

剩余必须继续收敛：Operations Console 内部 `PageToolbar` / `SurfaceCard` / `MetricCard` / `StatePanel` 五态、操作错误态、后端刷新真值、权限态以及 Runtime correlation。

### P1-07-A Audit

第一轮完成审计页公共壳层与 Runtime correlation 基线：

- 新增 `AuditLogWorkbench.vue` 并统一使用 `PageHeader`；
- `/runtime/audit` 通过共享页面壳层进入既有 Audit 子工作台；
- Audit → Runtime 使用后端返回的 `execution_id` 构造 `/runtime?execution_id=...&source=audit`，不依赖表格位置或分页顺序；
- 保留现有 `StatePanel` 的 Loading / Permission / Error / Empty / Success 语义；
- Targeted：`frontend/tests/views/AuditLogUI03Correlation.test.ts`，**未执行**。

剩余必须继续收敛：Audit 内部 `PageToolbar` / `SurfaceCard` 一致性，以及与 Runtime focused durable facts 的回归覆盖。

### P1-08-A Dashboard

Dashboard 已建立公共 UI 模式，本轮补齐最近执行的 durable deep link：

- 最近执行不再只能进入 `/runtime` 首页；
- 用户点击具体 Execution 时使用该行后端返回的 `execution_id`；
- 深链为 `/runtime?execution_id=<real-id>&source=dashboard`；
- 不根据数组第一项、时间或分页位置推断目标执行。

Targeted：`frontend/tests/views/DashboardConsistency.test.ts`，**未执行**。

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

当前策略：**继续推进主线任务开发，并分阶段完成测试脚本，但不执行测试，直到全部任务完成后再进行测试。**

当前所有测试记录必须使用：

- Targeted result：**未执行**
- Full unit：**未执行**
- Build：**未执行**
- Gate：**未执行**
- Real API / E2E：**未执行**

全部页面 Gap Audit、代码实现、targeted 测试脚本、文档和原子提交完成后，统一执行：

```text
targeted tests → npm run test:unit → npm run build → gate / E2E
```

## 7. 当前队列

1. P1-06-A Operations Console 内部 UI-03/UI-04/UI-05 与 Runtime correlation 收敛。
2. P1-07-A Audit 内部公共模式与 Runtime focused durable facts regression。
3. P1-08-A Dashboard consistency 收尾。
4. 全站一致性 Gap Audit：原始 `el-card` / 自定义状态 / action loading / optimistic mutation / deep link / durable ID / stale-data 清理。
5. 全部任务完成后统一执行测试与构建验证。

## 8. 原子任务记录规范

```text
### <Task ID>
- 页面/模块：
- Gap：
- Contract：
- 实现范围：
- Targeted test：
- Targeted result：未执行
- Full unit：未执行
- Build：未执行
- Gate：未执行
- Real API / E2E：未执行
- 已知限制/阻塞：
- Commit：
- 下一任务：
```
