# Frontend Full Vitest Regression Remediation — 2026-08-30 / 2026-09-03

## 1. 版本同步与当前基线

2026-09-03 本轮检查远端 `main` 与 `frontend`。`main` 当前为 `6110038ea027882617ff02352ab7afa10ac5a845`，此前 `frontend` 已同步至 `4180b55339106b2f922e3d6032399598dc4b14d8` 后完成本轮前端修复。由于 main 在前端修复过程中又新增了 1 个后端测试修复提交，本轮已将该最新 main 提交纳入 frontend，并以双父 merge commit 保持完整历史。

当前 `frontend` 与 `main` 的 merge base 已为最新 main，frontend 无落后提交；frontend 保留本轮前端修复提交。

本轮未修改后端业务 Contract；frontend 继续消费已确认的正式 API 类型与 Durable Facts。

## 2. 用户最新全量 Vitest 反馈

用户在 Windows `frontend` 工作树执行 `npm test`，本次反馈结果：

```text
Test Files  1 failed | 69 passed (70)
Tests       1 failed | 325 passed (326)
```

唯一失败项：

- `tests/views/FullSiteConsistencyStaticAudit.test.ts > full-site static consistency audit > keeps Operations Console toggles backend-truth based`
- 测试仍断言旧实现 `@change="toggleProvider(row as RuntimeProvider, $event)"` 与 `@change="toggleRule(row as RuntimeAlertRule, $event)"`。
- 当前生产代码为解决 `vue-tsc` 的严格模板类型错误，已经明确使用 `$event === true` 将 Element Plus `change` 事件收窄为 boolean；测试因此发生 Contract 漂移。

## 3. 根因分析

Element Plus `el-switch` 的模板 `change` 事件在当前类型环境中可能被推断为 `string | number | boolean`。生产处理函数要求严格 `boolean`，因此直接传递 `$event` 无法通过 `vue-tsc`。

本轮之前已经采用局部类型收窄：

```vue
@change="toggleProvider(row as RuntimeProvider, $event === true)"
@change="toggleRule(row as RuntimeAlertRule, $event === true)"
```

该实现没有改变后端 API Contract，也没有恢复 optimistic durable mutation；开关操作仍在后端请求成功后重新加载 Provider / Alert Rule，以后端事实作为页面最终状态。

因此本次失败不是生产代码回归，而是静态治理测试仍保留旧事件表达式。

## 4. 本轮最小修复

### 4.1 Operations Console 静态治理测试

更新 `FullSiteConsistencyStaticAudit.test.ts` 的两个精确断言，使测试契约与当前严格类型安全实现一致：

- Provider：断言 `toggleProvider(row as RuntimeProvider, $event === true)`；
- Alert Rule：断言 `toggleRule(row as RuntimeAlertRule, $event === true)`。

同时继续保留：

- `:model-value="row.enabled"`；
- 禁止 `v-model="row.enabled"`；
- 禁止 `Object.assign(row,r.data)`；
- 要求 `await loadProviders()`；
- 要求 `await loadAlerts()`。

原子提交：

`test: align operations console static audit with strict events`

## 5. 前序 build 类型修复

用户此前在 Windows 工作树执行 `npm run build`，发现 11 个 `vue-tsc` 模板类型错误，集中于三个页面：

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
- 禁止 View 层 optimistic durable status mutation；
- Operations Console 的 Provider / Alert Rule 开关必须通过 `:model-value` 呈现后端事实，并将 switch 事件显式收窄为 boolean；状态变更后必须重新读取后端事实。

这些规则是前端架构治理门禁：页面状态通过共享 primitive 表达，实体关系通过后端 durable ID / Contract 支撑。

## 8. 当前验证状态

本轮环境不能直接执行用户 Windows 工作树中的 `npm test` 或 `npm run build`，因此**不记录未经实际执行的“通过”**。

用户最新本地结果已经将失败从此前的 3 个测试文件 / 3 个测试收敛至 **1 个测试文件 / 1 个测试**；本轮已针对该唯一失败完成最小测试契约修复。

当前 `frontend` 最新提交为：

```text
6723dd6e1b91562ede8990e971c1d9fec0e7db1f
```

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
6723dd6e1b91562ede8990e971c1d9fec0e7db1f
```

然后执行本轮 targeted regression：

```powershell
npx vitest run tests/views/FullSiteConsistencyStaticAudit.test.ts
```

随后执行标准全量验证：

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

当前状态仍为 **进行中**：本轮唯一 Vitest 失败已经完成测试契约修复，但尚未由用户 Windows 工作树重新执行 targeted Vitest、全量 `npm test` 和 `npm run build` 验证。下一步先执行 targeted regression，再执行全量 test/build；若两项均通过，再进入 test gate 和 E2E。若仍失败，继续遵循“单一根因 → 最小修复 → targeted/full regression → 文档 → 原子提交”，不进行无关的大规模重构。
