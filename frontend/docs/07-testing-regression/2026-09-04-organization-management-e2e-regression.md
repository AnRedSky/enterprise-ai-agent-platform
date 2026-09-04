# Organization Management E2E 回归记录 — 2026-09-04

## 1. 回归输入

本次修复基于本地 `frontend` 的真实 Playwright 反馈：

- `Organization management completes the real owner browser contract`：成员行存在，但 `编辑` 按钮在 60 秒内未出现。
- `Organization browser governance enforces member and suspended-member boundaries`：通过。
- `Organization owner transfer exposes owner-only browser controls`：固定 `browser_e2e_owner` 的 membership 已为 `admin`，测试在 owner 角色断言处失败。

## 2. 根因

### 2.1 页面权限上下文错误

组织详情页原先直接从当前渲染页 `members` 数组推导当前用户 membership：

```ts
members.value.find((member) => member.user_id === getUserId())
```

成员列表是后端分页结果，当前用户不一定出现在当前页。因此页面可能已经拿到目标成员行，却因为当前用户 membership 不在该页而错误隐藏整个管理操作列。

### 2.2 E2E 测试数据污染

owner transfer 测试依赖固定 `browser_e2e_owner` 与持久 Organization。此前测试失败或中断后，owner 角色可能已经被转移，后续测试再次读取同一 durable 数据时就会得到 `admin`，导致 owner 断言失败。

## 3. 修复方案

### 前端

`frontend/src/views/organizations/detail.vue` 新增独立的 `currentMembership` 权限上下文：

- 页面加载后通过既有 `GET /organizations/{organization_id}/members` Contract 分页查找当前用户 membership；
- 页面展示分页仍保持原有 `20` 条/page，不改变后端分页或业务规则；
- `canManage` / `canTransferOwner` 只依赖真实当前 membership，而不是当前 UI 页；
- owner transfer 成功后重新读取当前 membership，保证 owner → admin 的权限变化立即反映到 UI。

### E2E

`Organization owner transfer exposes owner-only browser controls` 改为每次运行动态注册 owner、创建唯一 Organization、注册动态目标用户并执行完整 owner transfer 流程。

这样测试数据具备单次运行唯一性，不依赖固定 Organization 的历史 role 状态，也不通过修改生产数据来“修复”测试。

## 4. Contract 对齐

后端正式 Organization Contract 仍为：

- `GET /organizations/{organization_id}`：验证当前用户 active membership；
- `GET /organizations/{organization_id}/members?offset=&limit=`：分页返回真实 membership；
- `POST /organizations/{organization_id}/members/{membership_id}/transfer-owner`：仅当前 owner 可执行；
- owner transfer 后原 owner 降级为 `admin`，目标 active membership 升级为 `owner`。

本次未修改后端业务规则、分页参数或状态机。

## 5. 验证要求

本地环境中应按以下顺序执行，且不得自动启动服务或手工填写测试数据：

```powershell
npm install
npm run test:e2e -- tests/e2e/organization-management.spec.ts
npm test -- tests/views/...
npm test
npm run build
npm run test:gate
```

其中 E2E 依赖已运行的本地前后端服务，但测试数据由脚本通过注册、创建 Organization、添加 membership 自动生成。

## 6. 当前状态

- main 已同步至历史 `frontend` 分支状态后继续修复；
- 页面权限上下文修复已提交；
- owner transfer E2E 隔离修复已提交；
- 本文档记录本次失败事实、根因和验证方式；
- 在用户本地重新执行 E2E 前，不将结果标记为“通过”。
