# Organization Management E2E 回归记录 — 2026-09-04

## 1. 回归输入

本次修复基于用户本地 `frontend` 的真实 Playwright 反馈：

- `Organization management completes the real owner browser contract`：成员暂停成功后，5 秒内未捕获 `成员已暂停` 通知；成员状态断言尚未执行。
- `Organization browser governance enforces member and suspended-member boundaries`：通过。
- `Organization owner transfer exposes owner-only browser controls`：为动态注册用户创建第二个 Organization 的请求返回非 2xx；原因是当前认证注册契约会把新用户加入默认 Organization，而 Organization 创建服务要求当前 Tenant 尚未存在 Organization。

## 2. 根因

### 2.1 页面权限上下文错误

组织详情页原先直接从当前渲染页 `members` 数组推导当前用户 membership。成员列表是后端分页结果，当前用户不一定出现在当前页，因此页面可能已经拿到目标成员行，却错误隐藏管理操作列。

该问题已在前一提交通过独立 `currentMembership` 权限上下文修复。

### 2.2 E2E owner transfer 测试与后端注册/Organization 创建契约不一致

当前后端 `POST /auth/register` 会将新注册用户自动加入默认 Tenant 对应的 Organization；同时 `POST /organizations` 只允许在当前 Tenant 尚未存在 Organization 时创建 Organization。因此 owner-transfer E2E 为动态注册 owner 再创建第二个 Organization 的数据准备方式与真实后端契约冲突，并非前端业务故障。

### 2.3 成功通知是瞬时 UI 状态

Element Plus `ElMessage` 是短生命周期通知。原测试在完成 `updateMember`、重新加载成员列表后才开始等待 `成员已暂停`，如果操作链耗时超过通知生命周期，DOM 中已经不存在该文本，从而产生时序型失败。

## 3. 本次修复方案

### E2E 通知捕获

`frontend/tests/e2e/organization-management.spec.ts` 新增 `waitForMessage()`，在触发操作前建立对 `document.body.innerText` 的等待：

- 保留原来的精确业务通知文本断言；
- 将等待订阅建立在点击动作之前，避免短生命周期通知因等待时机而丢失；
- 未修改测试总超时 `60_000ms`，未降低任何业务状态断言。

### E2E owner transfer 数据准备

owner-transfer 场景继续使用 deterministic `browser_e2e_owner` 作为真实 owner，但目标用户每次运行动态注册。

- 新注册目标用户按照正式认证契约自动获得默认 Organization 的 `active/member` membership；
- 测试直接通过 `GET /organizations/{organization_id}/members` 获取该真实 membership ID，不重复调用必然冲突的 Organization 创建接口；
- 仍执行真实 owner transfer API 与浏览器权限边界验证；
- 成功转移后恢复原 owner；
- 若 UI 断言在转移完成后失败，`finally` 会尝试使用动态新 owner 恢复原 owner，避免 durable owner fixture 被污染。

### 后端边界

本次未修改后端 Organization 创建、注册、成员分页、membership 状态机或 owner transfer 业务逻辑。

## 4. Contract 对齐

后端正式 Organization Contract：

- `POST /auth/register`：新用户加入默认 Organization，初始 membership 为 `active/member`；
- `GET /organizations`：按用户 active membership 返回 Organization；
- `GET /organizations/{organization_id}/members?offset=&limit=`：分页返回真实 membership；
- `POST /organizations/{organization_id}/members/{membership_id}/transfer-owner`：仅当前 owner 可执行；
- owner transfer 后原 owner 降级为 `admin`，目标 active membership 升级为 `owner`；
- `POST /organizations`：当前 Tenant 已存在 Organization 时返回业务冲突。

## 5. 验证要求

本地环境保持现有服务运行，不由测试脚本自动启动服务。测试数据全部由 Playwright API 脚本生成。

先执行一次 deterministic Browser E2E 数据重置，确保 durable owner fixture 为 `active/owner`：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
python scripts/test/e2e/00_reset_browser_e2e_database.py
```

然后进入 frontend 执行 targeted E2E：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend
npm run test:e2e -- tests/e2e/organization-management.spec.ts
```

只有 targeted E2E 三项全部通过后，才继续：

```powershell
npm test
npm run build
npm run test:gate
```

## 6. 本次反馈后的状态

- 页面权限上下文修复已存在于 `frontend`；
- 本次针对瞬时通知时序和 owner-transfer 数据准备契约进行修复；
- 未弱化断言、未调整测试超时、未修改后端生产分页或业务规则；
- targeted E2E 仍需由用户本地 Windows + Playwright 环境实际执行确认；
- 在用户本地重新执行前，不将测试结果标记为“通过”。
