# Frontend Full Vitest / Browser E2E Regression Remediation — 2026-08-30 / 2026-09-03

## 1. 版本同步与当前基线

2026-09-03 本轮检查远端 `main` 与 `frontend`。最新 `main` 为：

```text
164e79fcabbddcc4b0f974a32d93c530be4ce62f
```

此前 `frontend` 为 `02fe9e092779194b1e95d0f9cd7ea8f9a8e92d98`，比较结果显示 `frontend` 是 `main` 的祖先，`main` 领先 10 个提交且无分叉。因此本轮按 fast-forward 方式将 `frontend` 同步到最新 `main`，不制造无意义的 merge commit。该做法符合当前前端开发准则“直接基于 main”的分支治理要求。

最新 `main` 的后端变化集中在 Operator Governance 幂等冲突、事务回滚、集成/单元验收和项目状态文档；未发现与本轮三个 Browser E2E 失败直接冲突的前端 Contract 变更。

同步后针对用户最新 Browser E2E 反馈完成三项最小测试契约修复：

- Organization E2E：使用注册接口已经建立的默认 Organization membership，不再重复调用成员新增接口；
- Workflow Trigger E2E：通过页面实际的“选择 Workflow”文本区域打开 Select，完成显式 Workflow 选择；
- Model Provider E2E：从真实浏览器 POST `/api/v1/model-providers` 的 201 响应取得持久化 Provider ID，再 reload 页面验证 UI 可见性。

本轮未修改后端业务 Contract。

## 2. 用户最新 Browser E2E 反馈

用户在 Windows `frontend` 工作树执行 targeted Playwright：

```text
organization-management.spec.ts
3 failed

workflow-trigger-governance.spec.ts
1 failed

model-provider-governance.spec.ts
1 failed, 1 passed
```

对应失败表现：

1. Organization 三个场景：`POST /organizations/{organization_id}/members` 返回 `409`，测试原本强制期待 `201`。
2. Workflow Trigger：`getByRole("combobox").first().click()` 被 Element Plus Select 内部 placeholder `<span>` 拦截，60 秒超时。
3. Model Provider：保存成功提示后，独立 API list 查询中没有找到本次 Provider，断言得到 `undefined`。

## 3. 根因分析

### 3.1 Organization E2E 重复建立 membership

最新 Backend Contract 中，`POST /auth/register` 已明确在默认 Tenant 对应 Organization 中创建 active/member membership。组织服务的 `add_member()` 同时明确：如果用户已经属于该 Organization，则返回 HTTP 409。

因此，原 E2E 在注册用户后再次调用：

```text
POST /organizations/{organization_id}/members
```

属于重复写入，得到 `409 用户已经属于该 Organization` 是符合后端 Contract 的正常行为，而不是生产代码故障。

修复策略：删除 E2E 中重复的 `addMember()` helper 和调用点，注册后直接通过真实 `GET /organizations/{organization_id}/members` 获取已经持久化的 membership。

### 3.2 Workflow Trigger Select 的 locator 命中内部 input

页面的 Workflow 选择器使用 Element Plus `el-select`。`getByRole("combobox").first()` 命中内部 readonly input；用户反馈中的 Playwright 日志明确显示 placeholder `<span>选择 Workflow</span>` 拦截 pointer event。

修复策略：使用用户实际可交互的 placeholder 文本：

```ts
await page.getByText("选择 Workflow", { exact: true }).click();
```

随后仍通过真实 Workflow 名称与后端状态组成的 option 文本完成选择，不通过数组位置或本地推断关系。

### 3.3 Model Provider 测试不应依赖独立 list 查询定位刚创建资源

页面保存逻辑调用真实 `POST /api/v1/model-providers`，后端创建接口在 commit 后返回完整 `ModelProviderResponse`。用户反馈显示保存成功消息已经出现，但测试随后通过独立 list 查询寻找本次 Provider 得到 `undefined`。

测试的核心目的其实是验证：

```text
浏览器创建操作 → 后端真实持久化 → 页面重新读取 → Provider 可见 → 创建 Profile
```

因此无需用另一个 list 查询去猜测刚创建对象。修复为直接等待真实浏览器 POST response，断言 HTTP 201、organization_id、name、provider_name，并使用 response 中的持久化 `id` 继续后续 Profile API 验证；然后 reload 页面确认 Provider UI 可见。

这避免了增加任意 timeout，也没有修改生产 Model Provider 页面或后端服务。

## 4. 本轮原子修复

### 4.1 Organization membership fixture

提交：

```text
4b57b7b27a26a448b9cbb5ae726537e04379a093
```

提交信息：

```text
test: align organization E2E fixture with registration membership contract
```

变更：

- 删除重复 `addMember()` helper；
- 三个场景均在注册后直接读取后端已经建立的 membership；
- 保留真实角色、暂停、恢复、组织暂停、owner transfer 等 Browser Contract 验证。

### 4.2 Workflow Trigger stable selector

提交：

```text
108fae87aa8518bc0bf7eec40b40a8bbb9a88a31
```

提交信息：

```text
test: use stable workflow selector in trigger E2E
```

变更：

- 不再点击 Element Plus Select 内部 combobox input；
- 通过页面可见的 `选择 Workflow` 交互文本打开选择器；
- 后续仍按真实 Workflow 名称和状态选择 option。

### 4.3 Model Provider persisted response contract

提交：

```text
7cc59a5ba75c907ad602c7b981ea94bdedb8886f
```

提交信息：

```text
test: verify model provider creation from persisted API response
```

变更：

- 等待真实浏览器 `POST /api/v1/model-providers` response；
- 断言 HTTP 201 和后端返回的 Provider durable ID / organization scope / name；
- 使用返回的 Provider ID 创建 Model Profile；
- reload 页面验证 Provider UI 重新从真实 API 恢复。

## 5. 前序 Vitest / build 类型修复

此前用户在 Windows 工作树执行 `npm test`，发现 11 个 `vue-tsc` 模板类型错误，集中于三个页面：

- `integrations/OperationsConsole.vue`：Element Plus `el-switch` 的 `change` 事件在模板中推断为 `string | number | boolean`，而运行时操作函数只接受 boolean；Audit table slot 的 `row` 同时被推断为 `DefaultRow`。
- `organizations/detail.vue`：`organization` 在成功分支中业务上非空，但 Vue 模板类型收窄不会跨 sibling 状态分支传播。
- `organizations/model-providers.vue`：Element Plus table slot 的 `row` 被推断为 `DefaultRow`，而编辑/删除函数要求 `ModelProfile`。

修复策略保持局部、类型安全且不放宽全局 `strict` / `vue-tsc`：

1. `OperationsConsole.vue`：switch 事件使用 `($event === true)` 收窄为 boolean；Audit slot 在进入 `executionIdOf` 前显式收窄为 `RuntimeAudit`。
2. `organizations/detail.vue`：成功分支使用专用 computed 完成非空收窄，不改变 API 请求和权限逻辑。
3. `organizations/model-providers.vue`：仅在 ModelProfile 编辑/删除动作边界将 table row 收窄为 `ModelProfile`。

## 6. Full-site Governance Contract

`FullSiteConsistencyStaticAudit.test.ts` 当前约束：

- 禁止原始 `el-card / el-empty / el-result`；
- 禁止 `v-loading` 页面指令；
- 禁止 `items / versions / destinations / providers / triggers` 使用 `[0]` 推导 durable relationship；
- 禁止通过 `sort()` / `reverse()` 建立实体关系；
- 禁止 View 层 optimistic durable status mutation；
- Operations Console 的 Provider / Alert Rule 开关必须以 boolean 事件收窄，并在状态变更后重新读取后端事实。

这些规则是前端架构治理门禁：页面状态通过共享 primitive 表达，实体关系通过后端 durable ID / Contract 支撑。

## 7. 当前验证状态

本轮无法直接执行用户 Windows 工作树中的 Browser E2E，因此**不记录未经实际执行的“通过”**。

用户提供的 targeted E2E 结果仍属于失败基线；本轮仅完成代码级根因修复。

当前 `frontend` HEAD 为：

```text
7cc59a5ba75c907ad602c7b981ea94bdedb8886f
```

其中前三项测试修复提交依次位于最新 main 之后：

```text
4b57b7b27a26a448b9cbb5ae726537e04379a093
test: align organization E2E fixture with registration membership contract

108fae87aa8518bc0bf7eec40b40a8bbb9a88a31
test: use stable workflow selector in trigger E2E

7cc59a5ba75c907ad602c7b981ea94bdedb8886f
test: verify model provider creation from persisted API response
```

GitHub Combined Status 尚未提供本轮这些提交的可用 status check，因此不记录 CI 通过。

## 8. 本地同步与验证顺序

先同步：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend

git fetch origin
git checkout frontend
git pull --ff-only origin frontend
git rev-parse HEAD
```

预期 HEAD：

```text
7cc59a5ba75c907ad602c7b981ea94bdedb8886f
```

首先执行三个 targeted Browser E2E：

```powershell
npx playwright test tests/e2e/organization-management.spec.ts
npx playwright test tests/e2e/workflow-trigger-governance.spec.ts
npx playwright test tests/e2e/model-provider-governance.spec.ts
```

若三组均通过，再执行：

```powershell
npm run test:e2e
```

随后执行标准前端验收：

```powershell
npm test
npm run build
npm run test:gate
```

如果任一 targeted E2E 仍失败，应先保存 Playwright screenshot / trace，并继续按“单一根因 → 最小修复 → targeted regression → 文档 → 原子提交”处理，不增加任意等待时间掩盖失败。

## 9. 本地手动验证流程

1. **Organization**：注册测试用户后确认其默认 Organization membership 已存在；验证 owner/member/suspended/transfer-owner 权限边界。
2. **Workflow Trigger**：打开页面后显式选择 Workflow，确认 Trigger 创建、Scheduler 状态、禁用和删除均来自真实 API。
3. **Model Provider**：创建 Provider 后确认浏览器 POST 返回 201 和 durable ID，reload 后确认 Provider 可见，再创建 embedding Model Profile 并核验 dimension。
4. **页面状态**：继续执行既有 UI-04 Loading / Empty / Error / Permission / Success 回归清单。
5. **响应式**：检查操作区、表格、状态面板和 Provider Card 在小屏宽度下无明显溢出。

测试数据必须由 Fixture / Script 自动生成，不得要求手工填写业务信息，也不得自动启动 API、Scheduler、Worker、PostgreSQL、Redis。

## 10. 下一步

当前状态仍为 **进行中**。下一优先级是让用户 Windows 工作树重新执行三个 targeted Browser E2E。如果全部通过，再执行完整 `npm run test:e2e`、`npm test`、`npm run build`、`npm run test:gate`。若出现新的失败，只修复当前实际 Contract / UI 行为对应的单一根因，禁止通过放宽断言或任意增加 timeout 制造假绿。
