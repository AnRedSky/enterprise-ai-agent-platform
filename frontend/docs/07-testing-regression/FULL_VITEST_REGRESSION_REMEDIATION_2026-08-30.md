# Frontend Full Vitest / Browser E2E Regression Remediation — 2026-08-30 / 2026-09-04

## 1. 版本同步与当前基线

2026-09-04 已重新检查远端 `main` 与 `frontend`。当前远端 `main` 为：

```text
12223ae982410745abcdc20262e1f1a28f8ed1c4
```

`frontend` 已通过 fast-forward 包含该 `main`，随后继续追加 Organization E2E 原子修复；当前相对 `main` 为 `ahead 1 / behind 0`。

最新 `main` 同时包含 Operator/Trigger transaction boundary 与 acceptance fixture 修复，不改变前端 Organization API Contract。

## 2. 用户最新 Browser E2E 反馈

用户在 Windows `frontend` 工作树执行：

```text
organization-management.spec.ts
3 failed
```

三个场景均在 `POST /organizations` 前置 fixture 收到：

```text
Expected: 201
Received: 409
```

同时：

```text
workflow-trigger-governance.spec.ts
1 passed

model-provider-governance.spec.ts
2 passed
```

## 3. 根因分析

### 3.1 Organization E2E 错误地假设“注册用户 = 新 Tenant = 可创建新 Organization”

当前后端注册 Contract 会把新注册用户绑定到 `DEFAULT_TENANT_ID` 对应的既有 Organization，并创建 active membership。后端 Organization 又明确限制一个 Tenant 只能存在一个 Organization。

因此 E2E 中为每个场景注册唯一 owner identity 后再调用 `POST /organizations`，会命中：

```text
409 当前 Tenant 已存在 Organization
```

这不是用户名、组织名称冲突，也不是 Playwright 并发问题，而是测试 fixture 与最新后端注册/租户治理 Contract 不一致。后端路由的创建接口仍返回 201 成功 Contract，但 service 层会在当前 Tenant 已有 Organization 时返回 409。fileciteturn618file0L2-L5 fileciteturn625file0L2-L5

### 3.2 正确 fixture 是复用默认 Organization，而不是创建第二个 Organization

后端注册实现会把注册用户写入默认 Tenant，并自动创建该用户的 Organization membership；测试不应再次 `addMember`，否则会重复创建 membership。fileciteturn633file0L2-L5

因此 Organization Browser E2E 应：

1. 使用环境变量 `BROWSER_E2E_OWNER_USERNAME/PASSWORD` 对应的持久 owner fixture；
2. owner 登录后通过 `/organizations` 获取其 Tenant 对应的 Organization；
3. 每个场景仅注册新的测试成员；
4. 直接通过真实 membership API 查找注册用户已经拥有的 membership；
5. durable owner transfer 场景完成后恢复原 owner；
6. suspended-member 场景断言完成后恢复成员状态。

### 3.3 Organization UI selector 与分页修复继续保留

生产页面不修改。测试继续使用：

- `heading[name="组织", exact=true]`；
- 组织 table row 按真实 `organization.name` 定位；
- 成员按真实 `user_id` 遍历 UI 分页；
- membership API 使用 `offset/limit` 查找真实 `user_id`；
- 不使用 `[0]`、`sort()` 或 `reverse()` 推断 durable relationship。

## 4. 当前原子修复

### 4.1 Organization fixture 与注册 Contract 对齐

```text
91bae8a74574909ce44401bd2e4325451682ed72
test: align organization fixtures with registration contract
```

变更：

- 恢复 `BROWSER_E2E_OWNER_USERNAME/PASSWORD` owner fixture；
- 移除每个场景创建第二个 Organization 的错误假设；
- 通过 `tenant_id` 精确定位 owner 所属 Organization；
- 保留唯一测试成员用户名，利用注册 API 自动产生真实 membership；
- 保留成员分页、UI semantic locator、durable assertions；
- owner transfer 和 suspended-member 测试均恢复 durable 状态，避免污染后续场景。

## 5. Workflow / Model Provider 已验证基线

用户当前反馈明确确认：

```text
workflow-trigger-governance.spec.ts
1 passed (5.1s)

model-provider-governance.spec.ts
2 passed (8.8s)
```

Workflow 修复使用真实 `Scheduler 持久化状态` SurfaceCard，不再依赖不存在的 `.scheduler-card` selector。

## 6. 当前分支状态

当前 `main`：

```text
12223ae982410745abcdc20262e1f1a28f8ed1c4
```

当前 `frontend`：

```text
91bae8a74574909ce44401bd2e4325451682ed72
```

关系：

```text
ahead 1 / behind 0
```

尚未把本轮 Organization fixture 修复合并回 `main`；`frontend` 保持单一原子提交，未 force push。

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

当前状态：**Organization fixture 修复已提交，等待 Windows targeted E2E 复验。**

下一步：

1. 用户同步最新 `frontend`；
2. 重新执行 Organization / Workflow Trigger / Model Provider 三个 targeted E2E；
3. 若全部通过，再进入 Full E2E / Vitest / build / gate；
4. 若 Organization 仍失败，仅针对新的真实 API/fixture 根因做最小原子修复；
5. 同步更新本文件，记录实际命令与结果。

禁止通过增加任意 timeout、放宽 locator、跳过 durable assertion、修改生产分页行为或创建第二个默认 Tenant Organization 来制造假绿。
