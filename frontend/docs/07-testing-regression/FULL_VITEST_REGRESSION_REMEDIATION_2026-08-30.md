# Frontend Full Vitest / Browser E2E Regression Remediation — 2026-08-30 / 2026-09-04

## 1. 版本同步与当前基线

2026-09-04 已重新检查远端 `main` 与 `frontend`。远端 `main` 当前为：

```text
56cdf95d6195f3fa70d504daf3f49243200623a9
```

此前 `frontend` 是 `main` 的祖先，本轮已将 `frontend` fast-forward 到该 `main` commit，因此本轮不是强制改写，也没有制造虚假 merge commit。随后新增的前端修复均直接提交到 `frontend`。

本轮 Browser E2E 修复均未修改后端业务 Contract；Workflow Scheduler 页面已经存在真实的 `Scheduler 持久化状态` SurfaceCard，测试应使用现有 UI semantic contract，而不是不存在的历史 `.scheduler-card` 选择器。

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

### 3.1 Organization 测试共享 durable organization fixture

Organization 测试此前依赖固定 owner 的既有组织，再向该组织追加随机成员。由于测试文件中的 owner transfer 是 durable mutation，前序运行可能改变固定组织的 owner；同时既有组织成员数量和分页顺序会持续增长，使“刚注册成员一定出现在第一页”或“下一页一定存在”的假设失效。

本轮修复改为：每个 Organization Browser E2E 场景由脚本通过真实 `POST /organizations` 创建独立、唯一命名的组织，再通过真实 `POST /organizations/{organization_id}/members` 添加随机测试用户。owner transfer 场景因此不再依赖共享组织的历史 owner 状态。

`getMembership()` 继续按 `offset/limit` 查找 durable membership ID，不使用 `[0]`、`sort()` 或 `reverse()` 推断关系。

### 3.2 Organization 列表入口必须定位刚创建的真实组织

测试仍保留真实 `/organizations` 列表入口，但不应假设某个数组位置就是刚创建的组织。测试应根据唯一组织名称定位对应 table row，再点击该 row 的 `管理成员` 深链。

当前 fixture 已改为唯一组织，生产分页保持不变，不通过修改业务页面分页来制造测试通过。

### 3.3 Workflow Scheduler 测试使用了不存在的旧 CSS selector

生产页面使用共享 `SurfaceCard`，Scheduler 区域的实际标题为 `Scheduler 持久化状态`，根节点 class 为共享组件的 `.ui-surface-card`，并不存在 `.scheduler-card`。

测试已改为以 `Scheduler 持久化状态` 标题限定 `.ui-surface-card`，再验证真实描述项中的 `时区=UTC`、`Misfire=skip`、`Catch-up Limit=10`。该方式直接表达当前 UI Contract，不新增平行 DOM 结构。

### 3.4 Workflow published status 与 trigger type selector

前序修复仍有效：publish 后重新 GET `/workflows/{workflow_id}`，断言 durable `status=published`，再使用 `(published)` 的 Workflow option；`scheduled` option 使用 `exact: true`，避免 Element Plus option 的非 exact 文本匹配导致 strict mode violation。

## 4. 本轮原子修复

### 4.1 Organization fixture isolation

```text
04cd15ec7efdc0b6c1f2ac897aebbacbb1cd7b59
test: isolate organization browser fixtures
```

变更：

- 每个 Organization 场景创建唯一测试组织；
- 使用真实 organization/member API 建立测试数据；
- owner transfer 场景不再依赖固定组织的历史 owner 状态；
- 保留真实 Browser UI 与 durable membership 验证。

### 4.2 Workflow Scheduler UI contract selector

```text
44ac4c222792eca9b977dee6399fbd3bc3d51747
test: align scheduler status selector with UI contract
```

变更：

- 移除不存在的 `.scheduler-card` 假设；
- 使用共享 `.ui-surface-card` + `Scheduler 持久化状态` 标题定位真实状态区域；
- 验证 UTC / skip / 10 三项持久化状态；
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

Provider fixture 使用 `000 E2E Provider <nonce>`，保证在当前按名称排序的首批数据中可见。

```text
b85558a85e46c1ecb2f753158f9e3a1288a501f7
test: stabilize organization pagination and owner fixtures
```

修复 Organization heading exact locator、StatePanel status semantics、成员分页浏览以及 transfer 后 owner 恢复。

```text
c56223b1e45122b288c9f4aef0c0d1f08f2d582c
test: use exact scheduled trigger type option
```

修复 Element Plus `scheduled` option 的 strict mode selector。

## 6. 用户实际验证结果

当前仅记录用户明确执行的结果：

```text
model-provider-governance.spec.ts
2 passed (9.3s)
```

Organization 与 Workflow Trigger 的本轮修复提交是在用户反馈之后完成的，**尚未由用户在其 Windows 工作树重新执行**，因此不能记录为通过。

## 7. 当前分支状态

本轮开始时：

```text
main = 56cdf95d6195f3fa70d504daf3f49243200623a9
frontend = main 的祖先
```

已执行 fast-forward：

```text
frontend -> 56cdf95d6195f3fa70d504daf3f49243200623a9
```

随后 `frontend` 新增两个原子修复 commit：

```text
04cd15ec7efdc0b6c1f2ac897aebbacbb1cd7b59
test: isolate organization browser fixtures

44ac4c222792eca9b977dee6399fbd3bc3d51747
test: align scheduler status selector with UI contract
```

本文件本次更新作为独立文档治理提交；最终 HEAD 以远端实际 branch 为准。

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

- 组织列表能够定位本次唯一创建的组织；
- 成员管理页显示随机测试成员；
- 编辑角色、暂停/恢复成员、暂停/恢复组织均成功；
- owner transfer 后新 owner 权限正确；
- transfer 后原 owner 可恢复，测试不会污染后续 durable state。

### Workflow Trigger

- 选择 durable published Workflow；
- 创建 Scheduled Trigger；
- 真实 API 能读取 Trigger 与 Scheduler 持久化状态；
- UI 的 `Scheduler 持久化状态` 显示 UTC / skip / 10；
- 禁用并删除 Trigger 后列表事实刷新。

### Model Provider

- 保持当前 2/2 通过基线；
- Provider fixture 在列表中稳定可见；
- 不引入第二套 API client 或状态枚举。

## 10. 当前状态与下一步

当前状态：**进行中，等待 Windows targeted E2E 复验**。

下一步严格按单一根因推进：

1. 用户同步最新 `frontend`；
2. 重新执行 Organization / Workflow Trigger / Model Provider 三个 targeted E2E；
3. 若全部通过，再进入 Full E2E / Vitest / build / gate；
4. 若仍失败，仅针对新的真实根因做最小原子修复；
5. 同步更新本文件，记录实际命令与结果。

禁止通过增加任意 timeout、放宽 locator、跳过 durable assertion、修改生产分页行为或复用共享 durable state 来制造假绿。
