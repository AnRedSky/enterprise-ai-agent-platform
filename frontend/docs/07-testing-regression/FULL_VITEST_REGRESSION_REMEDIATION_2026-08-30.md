# Frontend Full Vitest Regression Remediation — 2026-08-30 / 2026-09-03

## 1. 版本同步与当前基线

2026-09-03 本轮检查远端 `main` 与 `frontend`。`main` 当前为 `9b9d9f09a72810c26f97000608c9193dd4c9d4d4`，此前 `frontend` 已同步至 `b999a7dc26ea353824b8a11798afc8618f7595c2`。本轮发现 main 新增 6 个提交，已通过双父 merge commit `fe6ff0c3b0279df4abe4fb1a35a15da57e00aca7` 纳入 frontend，保持 frontend 自身历史与 main 最新后端修复完整合流。

本轮随后针对用户最新 Browser E2E 反馈完成两类测试契约修复：组织 E2E fixture 显式建立组织成员关系；Workflow Trigger E2E 显式选择 API 创建的 Workflow；Model Provider E2E 增加 API 持久化同步后重新加载页面的 UI 持久化校验。

本轮未修改后端业务 Contract；frontend 继续消费正式 API 类型与 Durable Facts。

## 2. 用户最新 Browser E2E 反馈

用户在 Windows `frontend` 工作树执行 `npm run test:e2e`：

```text
Running 8 tests using 5 workers

5 failed
3 passed (1.1m)
```

失败项：

1. `model-provider-governance.spec.ts:11`：创建模型提供方成功反馈后，5 秒内没有找到新 Provider 名称。
2. `organization-management.spec.ts:13`：注册新用户后，组织成员列表中找不到该用户。
3. `organization-management.spec.ts:28`：同上。
4. `organization-management.spec.ts:37`：同上。
5. `workflow-trigger-governance.spec.ts:24`：Workflow Trigger 页面等待 `Trigger 名称` 输入框超时。

## 3. 根因分析

### 3.1 Organization E2E fixture 与 Backend Membership Contract 不一致

最新 Backend Contract 提供显式的：

```text
POST /api/v1/organizations/{organization_id}/members
```

用于将已注册用户加入组织。注册用户本身不会自动成为 `browser_e2e_owner` 所属组织成员；原 E2E 直接注册用户后立即查询 owner 组织成员列表，因此 `membership` 为 `undefined`。

本轮不修改后端行为，而是让 E2E fixture 遵循正式组织成员 Contract：注册用户 → owner token → `POST /organizations/{organization_id}/members` → 查询持久化 membership。

### 3.2 Workflow Trigger E2E 未满足当前页面的显式 Workflow 选择 Contract

当前 Workflow Trigger 页面要求先显式选择目标 Workflow，之后才渲染 Trigger 名称、类型和操作区域。页面不会根据只有一个 Workflow 的事实自动选择目标，也不会通过数组位置推断关系。

原测试通过 API 创建并发布 Workflow 后直接访问 `/workflows/triggers`，随后立即查找 `Trigger 名称`，因此页面仍停留在“请选择 Workflow”状态，输入框根本不存在。

本轮测试先通过页面 Workflow combobox 选择刚由 API 创建的 Workflow，再进入 Trigger 创建流程。该修改与前端治理规则一致：实体关系必须由真实 Workflow ID / 显式选择建立，不依赖列表位置。

### 3.3 Model Provider E2E 的 UI 持久化观察需要与真实 API 持久化事实同步

用户反馈发生在“保存成功”提示之后，但 UI 未在默认 5 秒断言窗口内观察到新 Provider。后端正式 Contract 的 Provider 创建接口返回成功后由后端 commit 并 refresh，测试同时具备直接 API 查询能力。

本轮将该断言调整为：

1. 保存成功后直接通过 organization-scoped API 查询并确认 Provider 已持久化；
2. 浏览器重新加载当前页面；
3. 再确认新 Provider 在真实页面中可见；
4. 使用页面 Provider Card 继续创建 Model Profile。

这样既不通过延长任意 UI timeout 掩盖问题，也能明确区分“后端持久化失败”和“页面刷新观察失败”。

## 4. 本轮原子修复

### 4.1 Organization E2E membership fixture

提交：

```text
4e5c15bd6ee023ad499346f0c83e7d1e67cc0ddf
```

提交信息：

```text
test: align organization E2E fixture with membership contract
```

变更：

- 新增 `addMember()` 测试辅助函数；
- 三个组织 E2E 场景在 `getMembership()` 前显式调用组织成员 API；
- 不修改生产页面、API client 或后端 Contract。

### 4.2 Workflow Trigger explicit selection

提交：

```text
7e96ba01cc0d1695daf729d1412b2843b93acc98
```

提交信息：

```text
test: align workflow trigger E2E with explicit workflow selection
```

变更：

- 页面进入 Trigger 配置前显式选择 API 创建的 Workflow；
- 保持后续真实 Trigger / Scheduler / Execution API 验证不变；
- 不通过 `[0]` 或本地推断建立 Workflow/Trigger 关系。

### 4.3 Model Provider persistence synchronization

提交：

```text
51ac05c7015e7326af55b0d2299cf83a0055676c
```

提交信息：

```text
test: stabilize model provider E2E persistence check
```

变更：

- Provider 保存成功后先通过真实 organization-scoped API 确认持久化；
- 浏览器 reload 后确认 Provider UI 可见；
- 再继续 Model Profile 创建与 API 持久化断言；
- 不修改生产 Model Provider 实现。

## 5. 前序 Vitest / build 类型修复

用户此前在 Windows 工作树执行 `npm test`，发现 11 个 `vue-tsc` 模板类型错误，集中于三个页面：

- `integrations/OperationsConsole.vue`：Element Plus `el-switch` 的 `change` 事件在模板中推断为 `string | number | boolean`，而运行时操作函数只接受 boolean；Audit table slot 的 `row` 同时被推断为 `DefaultRow`，不能直接传给 `executionIdOf(RuntimeAudit)`。
- `organizations/detail.vue`：`organization` 在 `v-else` 成功分支中业务上已经非空，但 Vue 模板类型收窄不会跨 sibling `StatePanel` 分支传播，因此直接访问 `organization.name/id/status` 被判定为 nullable。
- `organizations/model-providers.vue`：Element Plus table slot 的 `row` 被推断为 `DefaultRow`，而编辑/删除函数要求 `ModelProfile`。

修复策略保持局部、类型安全且不放宽全局 `strict` / `vue-tsc`：

1. `OperationsConsole.vue`：对 switch 事件使用 `($event === true)` 明确收窄为 boolean；Audit slot 在进入 `executionIdOf` 前显式标注 `row as RuntimeAudit`。生产状态仍由后端成功结果刷新，不恢复 optimistic durable mutation。
2. `organizations/detail.vue`：新增成功分支专用 `organizationData` computed，在页面状态 Contract 已保证组织存在的前提下集中完成非空收窄；不改变 API 请求和权限逻辑。
3. `organizations/model-providers.vue`：仅在 ModelProfile 编辑/删除动作边界将 table row 显式收窄为 `ModelProfile`，不改变后端返回的数据结构。

## 6. Full-site Governance Contract

`FullSiteConsistencyStaticAudit.test.ts` 当前约束：

- 禁止原始 `el-card / el-empty / el-result`；
- 禁止 `v-loading` 页面指令；
- 禁止 `items / versions / destinations / providers / triggers` 使用 `[0]` 推导 durable relationship；
- 禁止通过 `sort()` / `reverse()` 建立实体关系；
- 禁止 View 层 optimistic durable status mutation；
- Operations Console 的 Provider / Alert Rule 开关必须通过 `:model-value` 呈现后端事实，并将 switch 事件显式收窄为 boolean；状态变更后必须重新读取后端事实。

这些规则是前端架构治理门禁：页面状态通过共享 primitive 表达，实体关系通过后端 durable ID / Contract 支撑。

## 7. 当前验证状态

本轮无法直接执行用户 Windows 工作树中的 Browser E2E，因此**不记录未经实际执行的“通过”**。

用户提供的 E2E 结果明确为 **8 个测试中 3 个通过、5 个失败**。本轮已针对 5 个失败按根因拆分并完成对应测试契约修复；这不等同于 E2E 已通过。

当前 `frontend` 最新提交为：

```text
51ac05c7015e7326af55b0d2299cf83a0055676c
```

GitHub Combined Status 当前没有返回任何 status check，因此不记录 CI 通过。

用户本地同步：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend

git fetch origin
git checkout frontend
git pull --ff-only origin frontend
git rev-parse HEAD
```

预期 HEAD：

```text
51ac05c7015e7326af55b0d2299cf83a0055676c
```

## 8. 推荐验证顺序

首先验证三个发生实际 Contract 调整的 E2E 文件：

```powershell
npx playwright test tests/e2e/organization-management.spec.ts
npx playwright test tests/e2e/workflow-trigger-governance.spec.ts
npx playwright test tests/e2e/model-provider-governance.spec.ts
```

如果三组均通过，再执行完整 E2E：

```powershell
npm run test:e2e
```

随后回到标准前端验收顺序：

```powershell
npm test
npm run build
npm run test:gate
```

没有实际执行的测试不得记录为通过；测试数据必须由 Fixture / Script 自动生成，不得要求手工填写业务信息，也不得自动启动 API、Scheduler、Worker、PostgreSQL、Redis。

## 9. 本地手动验证流程

1. Organization：注册测试用户后由脚本加入目标组织，确认 owner/member/suspended/transfer-owner 链路符合权限边界。
2. Workflow Trigger：打开页面后显式选择 Workflow，确认 Manual / Scheduled / Webhook Trigger 的创建、状态更新、删除和 Scheduler 状态来自真实 API。
3. Model Provider：创建 Provider 后确认 API 持久化，再 reload 页面确认 Provider UI 可见，继续创建 embedding Model Profile 并核验 dimension。
4. Dashboard / Knowledge / Audit / Agent / Tool / Operations Console：继续执行既有 UI-04 Loading / Empty / Error / Permission / Success 回归清单。
5. 小屏宽度：确认操作区、表格、状态面板和卡片保持可读，不产生明显布局溢出。

## 10. 下一步

当前状态仍为 **进行中**：本轮 E2E 失败已经完成最小测试契约修复，但尚未由用户 Windows 工作树重新执行。下一步优先执行三组 targeted Playwright；若通过，再执行完整 `npm run test:e2e`，之后执行 `npm test`、`npm run build` 和 `npm run test:gate`。若任一 targeted E2E 仍失败，继续遵循“单一根因 → 最小修复 → targeted regression → 文档 → 原子提交”，不进行无关的大规模重构。
