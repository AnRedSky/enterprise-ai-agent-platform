# Frontend Full Vitest / Browser E2E Regression Remediation — 2026-08-30 / 2026-09-04

## 1. 版本同步与当前基线

2026-09-04 继续检查远端 `main` 与 `frontend`。当前远端 `main` 为：

```text
6f7af7b5f373d51c94fd34e371ff141d28581bc4
```

当前 `frontend` 与 `main` 已发生分叉：`frontend` 相对 `main` ahead 3、behind 8。已创建 PR #90 尝试将 `main` 同步到 `frontend`，GitHub 当前报告 `mergeable=false`，因此本轮**未宣称同步完成**，也未强行改写分支历史。继续开发前应在本地执行真实 merge 并解决冲突，再推送到 `frontend`。

本轮 Browser E2E 修复均基于当前 `frontend` HEAD 提交，未修改后端业务 Contract。

## 2. 用户最新 Browser E2E 反馈

用户在 Windows `frontend` 工作树执行：

```text
organization-management.spec.ts
3 failed

model-provider-governance.spec.ts
2 passed
```

Organization 三个失败分别表现为：

1. `getByRole("heading", { name: "组织" })` 严格模式匹配 `组织` 与 `组织列表` 两个 heading；
2. suspended member 重新加载后等待 `role=alert`，但页面实际使用共享 `StatePanel`，其语义角色为 `status`；
3. owner transfer 场景在 API transfer 前置步骤收到非成功响应。

Model Provider 本轮用户反馈已全部通过 2/2；此前由 Provider 列表排序/分页导致的 fixture 不可见问题已通过 `000 E2E Provider <nonce>` fixture 修复。

## 3. 根因分析

### 3.1 Organization 列表 heading locator 不够精确

页面同时存在 `h1=组织` 和 `h2=组织列表`。Playwright `getByRole("heading", { name: "组织" })` 默认使用非 exact name 匹配，因此同时命中两个元素并触发 strict mode violation。

修复为：

```ts
page.getByRole("heading", { name: "组织", exact: true })
```

不修改生产 UI，仅让测试 locator 精确表达既有 UI Contract。

### 3.2 Organization error state 使用共享 StatePanel 的 status 语义

`organizations/detail.vue` 的加载错误通过共享 `StatePanel` 渲染。`StatePanel` 明确使用 `role="status"`，错误状态设置 `aria-live="assertive"`；不存在 `role="alert"`。

因此测试等待 `getByRole("alert")` 与公共状态组件 Contract 不一致。

修复为验证：

```ts
page.getByRole("status")
```

并同时验证 `当前用户无权访问该组织`，确保不仅验证“有错误状态”，还验证 403 permission boundary 被正确表达。

### 3.3 Owner transfer 测试污染后续测试的 durable organization state

Organization owner transfer 是 durable mutation。原场景完成 UI/API transfer 后没有恢复原始 owner，导致 Playwright worker 在同一个测试文件继续运行后，后续依赖固定 `browser_e2e_owner` 的场景可能失去 owner 权限，最终在 transfer API 前置步骤得到失败响应。

修复策略：transfer browser contract 验证成功后，使用刚成为 owner 的测试用户重新登录 API，定位原 owner 的真实 membership ID，再执行一次真实 `transfer-owner` 将所有权恢复。恢复动作仍使用 durable membership ID，不通过数组位置推断关系。

该修复保持测试数据自动生成，并避免测试之间共享不可控的 durable owner 状态。

## 4. 本轮原子修复

### 4.1 Organization UI semantic selectors

提交：

```text
06b415fc493ea9ac277f633b3b8b58c7e22c9d4f
```

提交信息：

```text
test: align organization E2E selectors with UI semantics
```

变更：

- `组织` heading 使用 `exact: true`；
- error StatePanel 使用 `role=status`，并校验 403 语义文案；
- 不修改生产组件。

### 4.2 Organization owner transfer fixture isolation

提交：

```text
138ec3a2dc5b898fda2063d1f1c1f9f3041487dc
```

提交信息：

```text
test: isolate organization owner transfer fixture state
```

变更：

- owner transfer Browser Contract 验证完成后恢复原 owner；
- 恢复时重新获取新 owner token，并通过真实 `user_id` 查找原 owner membership；
- 不使用 `[0]`、`sort()` 或 `reverse()` 推导实体关系。

### 4.3 Workflow published-status refresh

提交：

```text
6fca57e2a13ecccaa7219bfd125564da83ef9027
```

提交信息：

```text
test: refresh published workflow before trigger selection
```

变更：

- publish 后通过 `GET /workflows/{workflow_id}` 获取 durable Workflow；
- 断言 `status = published`；
- 页面 option 使用发布后的真实 status，而不是创建响应中的 stale `draft`。

### 4.4 前序 Organization membership pagination fixture

```text
44ffedd6467418389828e4814d02392a9c137f79
test: paginate organization membership fixture lookup
```

`getMembership()` 按 `offset=0,100,200...` 遍历，直到找到目标 `user_id` 或达到 `total`。

### 4.5 前序 Model Provider fixture ordering

```text
e947d39377150edf11bfe178513389738631c98d
test: stabilize model provider fixture ordering
```

Provider fixture 使用 `000 E2E Provider <nonce>`，确保在当前按名称排序、默认 limit=50 的首批数据中稳定可见。

## 5. 之前已验证的测试结果

用户本轮反馈确认：

```text
model-provider-governance.spec.ts
2 passed (9.3s)
```

此结果来自用户实际 Windows 工作树执行，记录为已验证。

Organization 和 Workflow Trigger 的最新修改尚未由用户在当前工作树重新执行，因此不记录为通过。

## 6. Governance Contract

继续遵循：

- 禁止原始 `el-card / el-empty / el-result`；
- 禁止 `v-loading` 页面指令；
- 禁止 `items / versions / destinations / providers / triggers` 使用 `[0]` 推导 durable relationship；
- 禁止通过 `sort()` / `reverse()` 建立实体关系；
- 禁止 View 层 optimistic durable status mutation；
- 状态变更后重新读取后端事实；
- 测试 locator 应表达真实 UI semantic contract，不通过宽泛 locator 掩盖 strict mode 问题；
- durable mutation 测试必须隔离或恢复共享 fixture 状态。

## 7. 当前验证状态

本轮**未执行 Windows 本地命令**，因此不能宣称 Organization / Workflow Trigger 已通过。

已完成代码提交：

```text
06b415fc493ea9ac277f633b3b8b58c7e22c9d4f
test: align organization E2E selectors with UI semantics

138ec3a2dc5b898fda2063d1f1c1f9f3041487dc
test: isolate organization owner transfer fixture state

6fca57e2a13ecccaa7219bfd125564da83ef9027
test: refresh published workflow before trigger selection
```

当前 `frontend` HEAD：

```text
138ec3a2dc5b898fda2063d1f1c1f9f3041487dc
```

随后还需要将 Workflow commit 和文档 commit 纳入最终同步历史；以 GitHub 当前实际 branch HEAD 为准，不以历史预期值代替。

## 8. 本地同步与验证顺序

由于 `main` 与 `frontend` 当前 diverged，先不要继续假定 fast-forward。建议：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend

git fetch origin
git checkout frontend
git status
git log --oneline --decorate -8
```

确认工作区干净后，在本地完成：

```powershell
git merge origin/main
```

如有冲突，按 `frontend/docs/00-governance/FRONTEND_DEVELOPMENT_GUIDELINES.md` 与当前 frontend 测试契约解决；解决后：

```powershell
git add <resolved-files>
git commit
```

然后推送：

```powershell
git push origin frontend
```

同步完成后执行 targeted：

```powershell
npx playwright test tests/e2e/organization-management.spec.ts
npx playwright test tests/e2e/model-provider-governance.spec.ts
npx playwright test tests/e2e/workflow-trigger-governance.spec.ts
```

全部 targeted 通过后再执行：

```powershell
npm run test:e2e
npm test
npm run build
npm run test:gate
```

## 9. 本地手动验证流程

1. **Organization**：确认组织列表标题、成员管理、成员角色/状态、组织暂停/恢复、owner transfer 均符合 UI Contract；owner transfer 完成后确认 fixture 不污染后续场景。
2. **Suspended boundary**：暂停测试成员后 reload，确认共享 `StatePanel` 展示 403 无权访问状态，而不是依赖不存在的 `alert` role。
3. **Workflow Trigger**：确认发布后的 Workflow option 显示 `(published)`，创建 Scheduled Trigger 后核验真实 Trigger 与 Scheduler 状态。
4. **Model Provider**：确认创建 POST 201、reload 后 `000 E2E Provider <nonce>` 可见，再创建 embedding Profile。
5. **响应式**：检查小屏操作区、表格、StatePanel、Provider Card 无明显溢出。

测试数据必须由 Fixture / Script 自动生成；不得手工填写业务数据；不得由 E2E 自动启动 API、Scheduler、Worker、PostgreSQL 或 Redis。

## 10. 下一步

当前状态仍为 **进行中**：

1. 先在本地将最新 `main` 合并到 `frontend`，解决当前分叉；
2. 同步后重新执行三个 targeted Browser E2E；
3. 若 targeted 全部通过，再执行 Full E2E / Vitest / build / gate；
4. 若出现新失败，只针对真实单一根因做最小修复，并同步测试文档与原子提交记录。

禁止通过增加任意 timeout、放宽 locator、跳过 durable state assertion 或共享测试状态的方式制造假绿。
