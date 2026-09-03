# Frontend Full Vitest Regression Remediation — 2026-08-30 / 2026-09-03

## 1. 版本同步与当前基线

2026-09-03 本轮检查远端 `main` 与 `frontend`。`main` 当前为 `4180b55339106b2f922e3d6032399598dc4b14d8`，此前 `frontend` 为 `87092b9643ac6a56f6fb07becbd55cf0b0d3c4dd`；比较结果为 `frontend` 落后 `main` 4 个提交、无 frontend 独有提交。由于 `main` 是从此前 frontend 提交继续演进的后代，本轮将 `frontend` fast-forward 至当前 `main`，确保最新后端测试与文档变更进入前端开发基线。

本轮未修改后端业务 Contract；frontend 继续消费已确认的正式 API 类型与 Durable Facts。

## 2. 用户最新本地全量 Vitest 反馈

用户在 Windows `frontend` 工作树执行 `npm test`，反馈结果：

```text
Test Files  3 failed | 67 passed (70)
Tests       3 failed | 323 passed (326)
```

失败项分为两类：

1. `DashboardUI03.test.ts`：测试使用 `shallowMount` 时未显式 stub `StatePanel`，导致共享状态组件被浅渲染为空壳，测试无法从 `wrapper.text()` 观察 `暂无运行记录`。
2. `DashboardUI04.test.ts`：测试仍要求“所有聚合数据为空”时页面必须进入顶层 empty；当前设计明确保留 Dashboard 工作区、常用入口和最近执行区域的 empty 状态，因此该断言已经与 UI-03/UI-04 的统一设计冲突。
3. `ToolWorkbenchUI03UI05.test.ts`：测试在 mount 后立即检查 loading DOM，没有等待 Vue 的下一次渲染 tick；`load()` 虽已同步把 `loading` 置为 `true`，DOM 断言时机仍早于更新。

## 3. 根因分析

### 3.1 Dashboard UI-03 shallow stub 边界

Dashboard 的空运行记录状态由 `StatePanel` 负责。`shallowMount` 会自动浅替换未显式 stub 的子组件，因此测试如果直接断言 `wrapper.text()`，并不能可靠观察 `StatePanel` 的用户可见文案。测试应显式提供最小 `StatePanel` stub，并同时验证 shared state class。

### 3.2 Dashboard UI-04 状态模型漂移

Dashboard 当前状态模型是：

- 聚合 API Loading / Permission / Error：页面级 StatePanel；
- 聚合 API 成功但没有运行记录：继续渲染 Dashboard workspace；
- 最近执行为空：在“最近执行” SurfaceCard 内显示 `StatePanel state="empty"`；
- 常用入口始终保持可用。

因此“全部数据为空 = 页面级 empty”已经不是当前产品 Contract。测试应验证用户可见的 empty 运行记录和快速导航，而不是要求旧版顶层 DOM 结构。

### 3.3 ToolWorkbench loading 断言时序

`ToolWorkbench.vue` 在 `onMounted(load)` 中同步设置 `loading=true`，但 Vue DOM 更新发生在下一次 tick。原测试 mount 后立即读取 `.state-panel`，会偶发/稳定地观察到后续初始空状态。该问题属于测试同步边界，不需要修改生产加载状态实现。

## 4. 本轮最小修复

### 4.1 Dashboard UI-03 测试

显式增加最小 `StatePanel` stub，并验证 `state-panel--empty`，保持对 `暂无运行记录`、智能体管理、工具管理、运行记录等用户可见契约的验证。

原子提交：

`test: assert dashboard empty state through shared state panel`

### 4.2 Dashboard UI-04 测试

将“顶层 empty”断言改为当前正式状态契约：验证最近执行 empty panel、`暂无运行记录` 和 6 个常用入口同时存在；保留 Loading / Permission / Error / Retry / Success / Unknown status 测试。

同时将 `SurfaceCard` 替换为可渲染 slot 的最小 stub，使测试直接验证 workspace 内容，而不是依赖组件自动 stub 的内部行为。

原子提交：

`test: align dashboard UI states with usable empty workspace`

### 4.3 ToolWorkbench UI-03/UI-05 测试

在 loading mount 后增加 `nextTick()`，等待 Vue 完成状态 DOM 更新，再断言 shared `StatePanel` 的 loading 状态。未改变 ToolWorkbench 的 API、权限、确认交互或 durable ID 行为。

原子提交：

`test: await tool loading state render`

## 5. 本轮 build 类型修复

用户随后在 Windows 工作树执行 `npm run build`，发现 11 个 `vue-tsc` 模板类型错误，集中于三个页面：

- `integrations/OperationsConsole.vue`：Element Plus `el-switch` 的 `change` 事件在模板中推断为 `string | number | boolean`，而运行时操作函数只接受 boolean；Audit table slot 的 `row` 同时被推断为 `DefaultRow`，不能直接传给 `executionIdOf(RuntimeAudit)`。
- `organizations/detail.vue`：`organization` 在 `v-else` 成功分支中业务上已经非空，但 Vue 模板类型收窄不会跨 sibling `StatePanel` 分支传播，因此直接访问 `organization.name/id/status` 被判定为 nullable。
- `organizations/model-providers.vue`：Element Plus table slot 的 `row` 被推断为 `DefaultRow`，而编辑/删除函数要求 `ModelProfile`。

修复策略保持局部、类型安全且不放宽全局 `strict` / `vue-tsc`：

1. `OperationsConsole.vue`：对 switch 事件使用 `($event === true)` 明确收窄为 boolean；Audit slot 在进入 `executionIdOf` 前显式标注 `row as RuntimeAudit`。生产状态仍由后端成功结果刷新，不恢复 optimistic durable mutation。
2. `organizations/detail.vue`：新增成功分支专用 `organizationData` computed，在页面状态 Contract 已保证组织存在的前提下集中完成非空收窄；不改变 API 请求和权限逻辑。
3. `organizations/model-providers.vue`：仅在 ModelProfile 编辑/删除动作边界将 table row 显式收窄为 `ModelProfile`，不改变后端返回的数据结构。

原子提交：

- `fix: narrow operations console template events`
- `fix: type model provider table rows`
- `fix: narrow organization detail template state`

这些修复没有修改后端 API Contract，也没有通过关闭 strict template checking 来隐藏真实类型问题。

## 6. 已完成的前序回归修复

以下修复仍属于当前回归基线：

- ToolWorkbench 测试 fixture 字符串边界修复；
- Agent 用户可见错误 fallback 断言对齐，并继续禁止 HTTP/provider 原始错误泄漏；
- Audit Log durable `execution_id` 关联改为语义断言；
- Audit Log shared-state ownership 测试定位到 `AuditLogPanel.vue`；
- Audit Log 成功刷新反馈 `审计日志已更新`；
- Dashboard 保留空运行记录状态和快速入口；
- Knowledge UI-04 成功态按 `.grid` 工作区语义断言。

## 7. Full-site Governance Contract

`FullSiteConsistencyStaticAudit.test.ts` 当前约束：

- 禁止原始 `el-card / el-empty / el-result`；
- 禁止 `v-loading` 页面指令；
- 禁止 `items / versions / destinations / providers / triggers` 使用 `[0]` 推导 durable relationship；
- 禁止通过 `sort()` / `reverse()` 建立实体关系；
- 禁止 View 层 optimistic durable status mutation。

这些规则是前端架构治理门禁：页面状态通过共享 primitive 表达，实体关系通过后端 durable ID / Contract 支撑。

## 8. 当前验证状态

本轮环境不能直接执行用户 Windows 工作树中的 `npm test` 或 `npm run build`，因此**不记录未经实际执行的“通过”**。当前已完成 main 同步、Vitest 失败分类、测试最小修复、build 类型错误根因定位、局部类型修复和文档同步。

用户本地同步最新 `frontend`：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend

git fetch origin
git checkout frontend
git pull --ff-only origin frontend
git rev-parse HEAD
```

同步后预期 HEAD：

```text
712c95fbce2c535c3792124cd0e80a5d9ee53a63
```

然后按标准顺序执行：

```powershell
npm test
npm run build
```

若两项均通过，再执行：

```powershell
npm run test:gate
npm run test:e2e
```

没有实际执行的测试不得记录为通过；测试数据必须由 Fixture / Script 自动生成，不得要求手工填写业务信息，也不得自动启动 API、Scheduler、Worker、PostgreSQL、Redis。

## 9. 本地手动验证流程

1. Dashboard 空数据：确认指标、常用入口和“暂无运行记录”同时可见。
2. Dashboard Loading：确认聚合请求未完成时显示 loading StatePanel。
3. Dashboard Permission/Error：确认 403 显示权限状态，普通失败显示错误与重试动作。
4. Knowledge Workbench：分别验证 Loading、Success、Empty、Error/Retry、Permission 状态。
5. Audit Log：确认首次 Loading、成功刷新反馈、Empty、Error、Permission 均使用 shared `StatePanel`。
6. Audit Log 深链：点击真实 `execution_id`，确认 Runtime URL 使用该 durable ID，不通过列表位置推断。
7. Agent Workbench：触发列表错误，确认只展示用户可读 fallback，不显示 HTTP/provider 原始错误。
8. Tool Workbench：确认 Loading、Error、Empty 状态均稳定，并验证启用/停用确认后按 durable `tool.id` 调用后端。
9. Operations Console：验证 Alert Rule / Provider 开关传入严格 boolean；Audit Execution 深链使用真实 audit durable row 数据。
10. Organization Detail：成功态确认组织信息正常渲染，Loading/Error/Empty 状态保持 shared `StatePanel`。
11. Model Providers：确认模型配置编辑、删除仍使用后端返回的 `ModelProfile.id`，并验证表格操作不依赖列表位置。
12. 小屏宽度：确认上述页面操作区、表格、状态面板和卡片保持可读，不产生明显布局溢出。

## 10. 下一步

当前状态仍为 **进行中**：本轮 build 类型修复已经提交到 `frontend`，但尚未由用户 Windows 工作树重新执行 `npm test` / `npm run build` 验证。下一步以用户最新验证结果为准；若两项均通过，再进入 test gate 和 E2E。若仍失败，继续遵循“单一根因 → 最小修复 → targeted/full regression → 文档 → 原子提交”，不进行无关的大规模重构。
