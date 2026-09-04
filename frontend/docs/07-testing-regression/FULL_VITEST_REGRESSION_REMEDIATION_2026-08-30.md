# Frontend Full Vitest / Browser E2E Regression Remediation — 2026-08-30 / 2026-09-04

## 1. 版本同步与当前基线

2026-09-04 已重新检查远端 `main` 与 `frontend`。当前远端 `main` 为：

```text
52c9ed9375e61425af7282b606006e8dd36a6976
```

`frontend` 已合并该 `main`，当前相对 `main` 为 `ahead 1 / behind 0`。

最新 `main` 同时包含 Operator/Trigger transaction boundary 与 acceptance fixture 修复，不改变前端 Organization API Contract。

## 2. 用户最新 Browser E2E 反馈

用户在 Windows `frontend` 工作树重新验证：

```text
organization-management.spec.ts
2 failed / 1 passed (7.8s)

workflow-trigger-governance.spec.ts
1 passed (4.7s)

model-provider-governance.spec.ts
2 passed (9.3s)
```

Organization 的两个失败分别为：

1. owner browser contract 在成员列表中无法通过旧的 Element Plus CSS wrapper selector 找到新注册成员；
2. owner transfer API 返回非 2xx。

## 3. 根因分析

### 3.1 Organization fixture 已正确对齐注册 Contract

当前后端注册 Contract 会把新注册用户绑定到 `DEFAULT_TENANT_ID` 对应的既有 Organization，并创建 active membership。Organization Service 同时限制一个 Tenant 只能存在一个 Organization。

因此 E2E 不再为每个场景创建第二个 Organization，而是：

1. 使用 `BROWSER_E2E_OWNER_USERNAME/PASSWORD` 持久 owner fixture；
2. owner 登录后通过真实 `/organizations` 获取当前 Tenant 的 Organization；
3. 每个场景注册唯一测试成员；
4. 直接读取注册产生的真实 membership；
5. transfer 完成后恢复原 owner；
6. suspended-member 场景结束后恢复 active 状态。

### 3.2 成员 UI 定位失败属于测试 selector 与渲染结构耦合

原实现使用：

```text
.el-table__body-wrapper tbody tr
```

该 selector 依赖 Element Plus 当前内部 DOM wrapper。用户反馈显示 API membership 已找到，但 Browser E2E 无法在渲染页面中找到对应行。

本轮最小修复改为基于用户可观察的 table row semantics：

```text
getByRole("row").filter({ hasText: userId })
```

分页仍然通过真实 UI 控件推进，不修改生产分页逻辑。

### 3.3 owner transfer 当前需要进一步验证 durable owner 状态

本轮用户反馈中的 transfer failure 发生在真实 API：

```text
POST /organizations/{organization_id}/members/{membership_id}/transfer-owner
```

后端正式 Contract 要求：

- actor 必须是 active owner；
- target membership 必须 active；
- 当前 Organization 必须恰好存在一个 active owner，且该 owner 必须是 actor。

因此本轮不通过修改生产权限逻辑或忽略 409 制造假绿。测试现在在 transfer 前显式断言 owner 与 target membership 的真实状态，并在失败时输出 HTTP status/body，便于区分持久测试数据污染、owner 状态异常和生产 Contract 问题。

## 4. 当前原子修复

### 4.1 Organization fixture 与注册 Contract 对齐

```text
91bae8a74574909ce44401bd2e4325451682ed72
test: align organization fixtures with registration contract
```

### 4.2 成员 locator 与 owner precondition 强化

```text
2193d4c1ee57461d8dd6632eef66e685fc673d25
test: stabilize organization member locator and owner preconditions
```

变更：

- 成员行使用 semantic table row locator；
- 分页切换后等待 active page 变化；
- transfer 前验证 owner fixture 的 membership 必须是 `active/owner`；
- transfer target 必须是 `active/member`；
- transfer API failure 保留真实 HTTP status/body 诊断上下文；
- 不修改生产 Organization Service。

## 5. Workflow / Model Provider 已验证基线

用户当前反馈明确确认：

```text
workflow-trigger-governance.spec.ts
1 passed (4.7s)

model-provider-governance.spec.ts
2 passed (9.3s)
```

Workflow 修复使用真实 `Scheduler 持久化状态` SurfaceCard，不再依赖不存在的 `.scheduler-card` selector。

## 6. 当前分支状态

当前 `main`：

```text
52c9ed9375e61425af7282b606006e8dd36a6976
```

当前 `frontend`：

```text
2193d4c1ee57461d8dd6632eef66e685fc673d25
```

关系：

```text
ahead 1 / behind 0
```

`main` 已通过 PR #91 合并进入 `frontend`；当前 frontend 仍保留一个独立的 Organization E2E 修复提交。

## 7. 本地验证顺序

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
npx playwright test tests/e2e/workflow-trigger-governance.spec.ts
npx playwright test tests/e2e/model-provider-governance.spec.ts
```

Targeted 全部通过后，再执行：

```powershell
npm run test:e2e
npm test
npm run build
npm run test:gate
```

遵循项目准则，E2E 不自动启动 API / Scheduler / Worker / PostgreSQL / Redis；测试数据由测试脚本自动创建，不要求手工填写业务数据。

## 8. 手动验收重点

### Organization

- 使用既有 Browser E2E owner 进入真实 Organization；
- 新注册成员自动出现在该 Organization membership 中；
- 组织列表根据真实 Organization 名称进入正确详情；
- 编辑角色、暂停/恢复成员、暂停/恢复组织均成功；
- owner transfer 前 owner/target membership 状态满足后端 Contract；
- owner transfer 后新 owner 权限正确；
- transfer 后恢复原 owner；
- suspended-member 场景结束后恢复成员 active 状态。

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

## 9. 当前状态与下一步

当前状态：**Organization E2E 仍进行中；Workflow Trigger 与 Model Provider targeted E2E 已通过。**

下一步：

1. 用户同步最新 `frontend`；
2. 重新执行 Organization targeted E2E；
3. 若 transfer 仍失败，使用新增 status/body 诊断信息确认 durable owner 状态是否异常；
4. 仅当真实 Contract/生产实现存在问题时修改后端；否则修复测试 fixture 或环境基线；
5. Organization 3/3、Workflow 1/1、Model Provider 2/2 全部通过后，再进入 Full E2E / Vitest / build / gate；
6. 同步更新本文件，记录实际命令与结果。

禁止通过增加任意 timeout、放宽 locator、跳过 durable assertion、修改生产分页行为或创建第二个默认 Tenant Organization 来制造假绿。
