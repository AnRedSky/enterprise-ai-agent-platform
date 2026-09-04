# Frontend Full Vitest / Browser E2E Regression Remediation — 2026-08-30 / 2026-09-04

## 1. 版本同步与当前基线

2026-09-04 本轮继续检查远端 `main` 与 `frontend`。最新 `main` 为：

```text
164e79fcabbddcc4b0f974a32d93c530be4ce62f
```

`frontend` 已基于该 main，当前未落后 main。本轮继续围绕用户 Windows targeted Browser E2E 反馈执行最小根因修复，不修改后端业务 Contract。

## 2. 用户最新 Browser E2E 反馈

用户执行三个 targeted Playwright：

```text
organization-management.spec.ts
3 failed

workflow-trigger-governance.spec.ts
1 failed

model-provider-governance.spec.ts
1 failed, 1 passed
```

失败表现：

1. Organization 三个场景：`getMembership()` 在组织成员列表第一页中找不到新注册用户。
2. Workflow Trigger：选择 Workflow 的 option 等待超时，测试期待 `E2E Scheduled Workflow ... (draft)`。
3. Model Provider：真实 POST 已返回 201，但页面 reload 后 5 秒内没有看到 Provider 名称。

## 3. 根因分析

### 3.1 Organization membership 查询错误地只检查第一页

当前 Backend Contract 中，`POST /auth/register` 已在默认 Tenant 对应 Organization 中创建 active/member membership；Organization service 的 `add_member()` 对已存在 membership 返回 409。后端成员列表同时支持 `offset` / `limit` 分页，并按创建时间升序返回。fileciteturn487file0 fileciteturn483file0 fileciteturn488file0

因此当前失败已经不再是“需要再次 add member”。上一轮删除重复 `addMember()` 后，`getMembership()` 仍只读取默认第一页；随着 E2E 数据积累，新 membership 可能位于第 2 页或之后。

本轮修复为分页遍历成员列表，直到找到目标 `user_id` 或 `offset + items.length >= total`。这避免通过数组位置推断关系，也不改变后端分页 Contract。

### 3.2 Workflow option 使用了创建时的 stale workflow status

测试通过 API 创建 Workflow 后取得的对象仍保存创建时的 `status = draft`。随后已经调用 publish API，但测试继续使用原对象中的 `workflow.status` 组成 option locator，因此期待：

```text
E2E Scheduled Workflow ... (draft)
```

而页面读取的是发布后的 durable Workflow，option 实际状态应为 `published`。

修复策略：发布后通过正式 `GET /workflows/{workflow_id}` 重新读取 durable Workflow，并断言 `status = published`，再使用真实名称和真实发布状态选择页面 option。当前这项代码修改已准备，但 GitHub Contents API 对该文件的连续写入返回 SHA 冲突，尚未提交，因此不得记录为已完成。

### 3.3 Model Provider UI 受后端列表排序/分页 Contract 影响

后端 `list_providers()` 按 `ModelProvider.name.asc()` 排序，并使用 `offset` / `limit` 分页。fileciteturn506file0

页面当前调用 `listModelProviders(organizationId)` 的默认 `limit=50`。因此 Browser E2E 使用普通 `Provider <nonce>` 名称时，如果组织中已有超过 50 个按名称排序靠前的 Provider，新建 Provider 可能不在页面首批 50 条数据中，即使创建接口已经成功返回 201。

本轮先采用**测试 fixture 最小修复**：Provider 名称改为 `000 E2E Provider <nonce>`，使自动生成的数据稳定位于当前字典序列表前部，从而验证本测试真正关注的“创建 → reload → UI 可见 → 创建 Profile”链路，而不依赖数据库已有测试数据数量。

该修复没有通过延长 timeout 掩盖问题，也没有修改生产分页行为。若实际环境仍能复现 Provider 创建后 reload 不可见，则下一步应检查浏览器 reload 时真实 GET response，而不是继续增加等待时间。

## 4. 本轮原子修复

### 4.1 Organization membership pagination fixture

提交：

```text
44ffedd6467418389828e4814d02392a9c137f79
```

提交信息：

```text
test: paginate organization membership fixture lookup
```

变更：

- `getMembership()` 从单页查询改为按 `offset=0,100,200...` 遍历；
- 使用后端返回的 `total` 作为停止条件；
- 仍以真实 `user_id` 建立 membership 关系，不使用 `[0]` 推断。

### 4.2 Model Provider fixture ordering

提交：

```text
e947d39377150edf11bfe178513389738631c98d
```

提交信息：

```text
test: stabilize model provider fixture ordering
```

变更：

- Provider 测试名称改为 `000 E2E Provider <nonce>`；
- 保留真实浏览器 POST 201 / durable ID 验证；
- 保留 reload 后 Provider UI 验证；
- 不修改生产 Model Provider 页面和后端服务。

### 4.3 Workflow published-status refresh

**状态：待提交。**

目标提交内容：

- publish 后通过 `GET /workflows/{workflow_id}` 获取最新 durable Workflow；
- 断言 `status = published`；
- 页面 option 使用最新 Workflow status，而不是 API 创建响应中的 stale `draft`。

当前 GitHub Contents API 连续更新该文件时返回 SHA mismatch，因此没有绕过原子提交规范强行制造替代提交。

## 5. 前序 Browser E2E 修复

此前已完成：

```text
4b57b7b27a26a448b9cbb5ae726537e04379a093
test: align organization E2E fixture with registration membership contract

108fae87aa8518bc0bf7eec40b40a8bbb9a88a31
test: use stable workflow selector in trigger E2E

7cc59a5ba75c907ad602c7b981ea94bdedb8886f
test: verify model provider creation from persisted API response
```

这些修复已经分别解决：重复创建 membership、Element Plus 内部 combobox locator、以及依赖独立 list 查询猜测 Provider 的测试契约问题。

## 6. 前序 Vitest / build 类型修复

此前已修复：

- `integrations/OperationsConsole.vue` 的 switch boolean 事件收窄及 table row 类型；
- `organizations/detail.vue` 的 nullable organization 模板类型；
- `organizations/model-providers.vue` 的 ModelProfile table row 类型；
- Full-site static audit 中与严格事件类型对应的断言。

保持全局 `strict` / `vue-tsc`，不通过放宽类型系统消除错误。

## 7. Full-site Governance Contract

继续遵循：

- 禁止原始 `el-card / el-empty / el-result`；
- 禁止 `v-loading` 页面指令；
- 禁止 `items / versions / destinations / providers / triggers` 使用 `[0]` 推导 durable relationship；
- 禁止通过 `sort()` / `reverse()` 建立实体关系；
- 禁止 View 层 optimistic durable status mutation；
- 实体关系必须使用后端 durable ID 或显式 UI 选择；
- 状态变更后重新读取后端事实。

## 8. 当前验证状态

本轮不能直接执行用户 Windows 工作树，因此**不记录未经实际执行的通过结果**。

用户最新结果仍是失败基线。本轮已经提交 Organization 分页 fixture 和 Model Provider fixture 两项修复；Workflow published-status 修复尚未提交。

当前 `frontend` 最新 HEAD：

```text
 e947d39377150edf11bfe178513389738631c98d
```

GitHub Combined Status 没有提供本轮新的可用 status check，因此不记录 CI 通过。

## 9. 本地同步与验证顺序

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend

git fetch origin
git checkout frontend
git pull --ff-only origin frontend
git rev-parse HEAD
```

预期 HEAD：

```text
e947d39377150edf11bfe178513389738631c98d
```

先执行：

```powershell
npx playwright test tests/e2e/organization-management.spec.ts
npx playwright test tests/e2e/model-provider-governance.spec.ts
```

Workflow Trigger 在 `workflow` 测试修复提交后再执行：

```powershell
npx playwright test tests/e2e/workflow-trigger-governance.spec.ts
```

全部 targeted 通过后：

```powershell
npm run test:e2e
npm test
npm run build
npm run test:gate
```

如仍失败，优先查看对应 screenshot / trace 和真实 API response，继续遵循“单一根因 → 最小修复 → targeted regression → 文档 → 原子提交”。

## 10. 本地手动验证流程

1. **Organization**：注册测试用户，确认默认 membership 存在；验证 owner/member/suspended/owner-transfer 权限边界。
2. **Workflow Trigger**：确认发布后的 Workflow 以 `published` durable status 出现在选择器中，再创建 Scheduled Trigger 并核验 Scheduler 状态。
3. **Model Provider**：创建 `000 E2E Provider <nonce>`，确认 POST 201 / durable ID，reload 后确认 Provider 可见，再创建 embedding Profile 并核验 dimension。
4. **状态治理**：继续执行 UI-04 Loading / Empty / Error / Permission / Success 回归。
5. **响应式**：检查小屏下操作区、表格、StatePanel、Provider Card 无明显溢出。

测试数据必须由 Fixture / Script 自动生成；不得手工填写业务数据；不得由 E2E 自动启动 API、Scheduler、Worker、PostgreSQL 或 Redis。

## 11. 下一步

当前仍为 **进行中**。下一优先级是提交并验证 Workflow published-status refresh，然后重新执行三个 targeted Browser E2E。若 targeted 全部通过，再进入完整 E2E 与 Vitest/build/gate 验收；若出现新失败，只针对真实 Contract / UI 行为的单一根因修复，不通过放宽断言或任意增加 timeout 制造假绿。
