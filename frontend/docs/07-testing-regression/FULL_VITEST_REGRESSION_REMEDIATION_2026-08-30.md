# Frontend Full Vitest / Browser E2E Regression Remediation — 2026-08-30 / 2026-09-04

## 1. 版本同步与当前基线

2026-09-04 已重新检查远端 `main` 与 `frontend`。当前远端 `main` 为：

```text
1b512fa8305301d3d262dc70f1425af6f014339e
```

`frontend` 已包含该 `main`，当前相对 `main` 为 `ahead 5 / behind 0`。本轮同步通过真实 merge commit 完成，没有 force push，也没有伪造 fast-forward 关系。

最新 `main` 同时包含 Operator Governance PostgreSQL acceptance fixture 修复：Retry 验收在创建 Workflow 前先建立 Tenant/User 外键事实；该修复不改变前端 API Contract。

## 2. 用户最新 Browser E2E 反馈

用户在 Windows `frontend` 工作树执行：

```text
organization-management.spec.ts
2 failed, 1 passed

workflow-trigger-governance.spec.ts
1 failed

model-provider-governance.spec.ts
2 passed
```

Organization 最新失败：

1. `showMemberRow()` 遍历 UI 分页后仍找不到刚注册成员；
2. owner transfer API 前置步骤失败。

Workflow Trigger 最新失败：

```text
locator(".scheduler-card") not found
```

Model Provider 已保持 2/2 通过。

## 3. 根因分析

### 3.1 Organization 测试仍存在共享 owner identity 风险

仅创建独立 Organization 仍不足以保证测试隔离：后端 Organization 与 Tenant 为一对一治理范围，固定 `browser_e2e_owner` 不能无限创建新的 Organization。多次测试运行还可能留下 durable membership / owner 状态。

因此最终方案不是继续复用固定 owner，而是每个 Organization Browser E2E 场景由脚本注册唯一 owner identity，再登录该 identity 创建唯一 Organization。这样每个测试拥有独立的 Tenant / Organization / owner membership 前置事实。

### 3.2 Organization 列表入口必须定位刚创建的真实组织

测试保留真实 `/organizations` UI 入口，但不再使用 `.first()` 假设新组织处于列表首位。测试根据本次唯一组织名称定位对应 table row，再点击该 row 的 `管理成员` 深链。

成员查询继续通过真实 `offset/limit` 分页查找目标 `user_id`，不修改生产页面的 20 条分页，也不使用 `[0]`、`sort()` 或 `reverse()` 推断关系。

### 3.3 Workflow Scheduler 测试使用了不存在的旧 CSS selector

生产页面使用共享 `SurfaceCard`，Scheduler 区域标题为 `Scheduler 持久化状态`，实际根节点是 `.ui-surface-card`，不存在 `.scheduler-card`。

测试已改为以 `Scheduler 持久化状态` 标题限定真实 SurfaceCard，并验证 `UTC`、`skip`、`10` 三项持久化状态，不新增平行 DOM 结构。

### 3.4 Workflow published status 与 trigger type selector

前序修复继续有效：publish 后重新 GET `/workflows/{workflow_id}`，确认 durable `status=published`，再选择 `(published)` Workflow；`scheduled` option 使用 `exact: true`，避免 Element Plus strict mode violation。

## 4. 当前原子修复

### 4.1 Organization owner identity isolation

```text
09f099f2baf1f34db2b85f3ffa2f1bd84431fba9
test: isolate organization owner identities
```

变更：

- 每个 Organization E2E 注册独立 owner identity；
- owner identity 登录后创建自己的 Organization；
- 每个场景拥有独立 Tenant / Organization / owner membership；
- Organization 列表根据唯一组织名称定位真实 row；
- 保留真实 Browser UI 与 durable API assertion。

### 4.2 Workflow Scheduler UI contract selector

```text
44ac4c222792eca9b977dee6399fbd3bc3d51747
test: align scheduler status selector with UI contract
```

变更：

- 移除不存在的 `.scheduler-card` 假设；
- 使用 `.ui-surface-card` + `Scheduler 持久化状态` 标题定位真实状态区域；
- 验证 UTC / skip / 10；
- 不修改生产 Scheduler 业务逻辑。

## 5. 前序已完成修复

```text
44ffedd6467418389828e4814d02392a9c137f79
test: paginate organization membership fixture lookup
```

`getMembership()` 按 `offset=0,100,200...` 查找目标 `user_id`。

```text
e947d39377150edf11bfe178513389738631c98d
test: stabilize model provider fixture ordering
```

Provider fixture 使用稳定的首批排序命名策略，避免测试依赖随机分页位置。

```text
c56223b1e45122b288c9f4aef0c0d1f08f2d582c
test: use exact scheduled trigger type option
```

修复 Element Plus `scheduled` option strict mode selector。

## 6. 用户实际验证结果

当前仅记录用户明确执行的结果：

```text
model-provider-governance.spec.ts
2 passed (10.3s)
```

Organization 与 Workflow Trigger 的最新修复提交是在用户反馈之后完成的，**尚未由用户在其 Windows 工作树重新执行**，因此不能记录为通过。

## 7. 当前分支状态

当前 `main`：

```text
1b512fa8305301d3d262dc70f1425af6f014339e
```

`frontend` 已包含 `main`，并继续包含本轮前端原子修复。最新 Organization fixture commit：

```text
09f099f2baf1f34db2b85f3ffa2f1bd84431fba9
test: isolate organization owner identities
```

本文件随后以独立文档治理提交更新；最终 HEAD 以远端实际 branch 为准。

## 8. 本地验证顺序

同步远端：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend
git fetch origin
git checkout frontend
git pull --ff-only origin frontend
```

Targeted Browser E2E：

```powershell
npx playwright test tests/e2e/organization-management.spec.ts
npx playwright test tests/e2e/model-provider-governance.spec.ts
npx playwright test tests/e2e/workflow-trigger-governance.spec.ts
```

Targeted 全部通过后，再执行：

```powershell
npm run test:e2e
npm test
npm run build
npm run test:gate
```

遵循项目准则，E2E 不自动启动 API / Scheduler / Worker / PostgreSQL / Redis；测试数据由测试脚本自动创建，不要求手工填写业务数据。

## 9. 手动验收重点

### Organization

- 本次测试 owner 能创建自己的唯一 Organization；
- 组织列表根据唯一组织名称进入正确详情深链；
- 成员管理页显示随机测试成员；
- 编辑角色、暂停/恢复成员、暂停/恢复组织均成功；
- owner transfer 后新 owner 权限正确；
- transfer 后原 owner 可恢复，不污染其他测试 owner。

### Workflow Trigger

- 选择 durable published Workflow；
- 创建 Scheduled Trigger；
- 真实 API 能读取 Trigger 与 Scheduler 持久化状态；
- UI 的 `Scheduler 持久化状态` 显示 UTC / skip / 10；
- 禁用并删除 Trigger 后列表事实刷新。

### Model Provider

- 保持当前用户反馈的 2/2 通过基线；
- Provider fixture 在列表中稳定可见；
- 不引入第二套 API client 或状态枚举。

## 10. 当前状态与下一步

当前状态：**等待 Windows targeted E2E 复验**。

下一步：

1. 用户同步最新 `frontend`；
2. 重新执行 Organization / Workflow Trigger / Model Provider 三个 targeted E2E；
3. 若全部通过，再进入 Full E2E / Vitest / build / gate；
4. 若仍失败，仅针对新的真实根因做最小原子修复；
5. 同步更新本文件，记录实际命令与结果。

禁止通过增加任意 timeout、放宽 locator、跳过 durable assertion、修改生产分页行为或复用共享 durable state 来制造假绿。
