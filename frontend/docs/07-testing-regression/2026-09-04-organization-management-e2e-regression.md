# Organization Management E2E 回归记录 — 2026-09-04

## 1. 回归输入

本轮继续基于用户本地 `frontend` 的真实 Playwright 反馈：

- `Organization management completes the real owner browser contract`：成员暂停操作前注册了 `waitForResponse`，但点击“暂停”只打开确认框，未确认，因此对应 PATCH 永远不会发出，最终触发 60 秒测试超时。
- `Organization browser governance enforces member and suspended-member boundaries`：通过。
- `Organization owner transfer exposes owner-only browser controls`：通过。

上一轮已经解决的 owner-only locator strict mode、current-membership 权限上下文以及瞬时成员 Toast 断言问题不重复实现。

## 2. 根因与判断

### 2.1 本轮失败是测试交互流缺失确认步骤

生产 `toggleMember()` 的真实交互顺序为：点击“暂停/恢复” → `ElMessageBox.confirm()` → 用户确认 → `PATCH /organizations/{organization_id}/members/{membership_id}` → 刷新成员列表 → 成功通知。测试此前在注册 `page.waitForResponse()` 后直接点击按钮并等待 PATCH，却没有确认 `ElMessageBox`，因此请求从未产生，最终等待超时。

这不是后端 API、权限或生产页面状态机问题，而是 Browser E2E 没有完整复现真实用户交互流。

### 2.2 成员状态成功事实仍不依赖瞬时 Toast

成员暂停/恢复操作真正稳定的成功事实是：

1. 用户确认状态变更；
2. 前端 PATCH 真实 membership endpoint 成功返回；
3. 页面重新加载成员列表；
4. 对应真实 membership 行最终展示后端返回的 `suspended` / `active` 状态。

因此 E2E 继续验证 API 响应 + 稳定 DOM 状态，而不是强制等待短生命周期 Toast。

### 2.3 owner transfer locator 作用域

组织 owner 可以向任意非 owner 成员转移所有权，因此详情页可能同时出现多个“转移所有权”按钮。当前测试继续明确表达 owner-only 控件语义：原 owner 数量为 `0`，新 owner 至少存在一个可见控件。

### 2.4 页面权限上下文

组织详情页的管理权限必须基于真实当前用户 membership，而不能从当前分页成员数组推导。当前生产代码已有独立 `currentMembership` 上下文和分页查找，本轮不重复实现。

## 3. 本轮修复

`frontend/tests/e2e/organization-management.spec.ts` 的成员暂停/恢复流程调整为完整真实交互链：

- 在点击“暂停”前注册 Playwright `waitForResponse`；
- 点击“暂停”后显式确认 `ElMessageBox`；
- 仅接受对应 organization + membership 的真实 `PATCH` 请求成功响应；
- 响应成功后等待成员行进入 `已暂停（suspended）`；
- 恢复操作采用相同模式，确认后等待真实 PATCH 成功并验证 `已启用（active）`；
- 不再把 `成员已暂停` / `成员已恢复` Toast 作为成员状态变更的强制 E2E 门槛。

组织暂停/恢复仍保留成功通知观察，因为这些操作的真实交互流已经包含确认步骤，且通知是当前页面已有的用户反馈契约。

本轮没有修改生产组织管理业务逻辑、后端权限规则或 API Contract。

## 4. Contract 对齐

当前 Organization Contract 使用真实资源 ID 和 membership ID：

- `POST /auth/register`：新用户加入默认 Organization，初始 membership 为 `active/member`；
- `GET /organizations`：按用户 active membership 返回 Organization；
- `GET /organizations/{organization_id}/members?offset=&limit=`：分页返回真实 membership；
- `PATCH /organizations/{organization_id}/members/{membership_id}`：更新真实 membership 的角色/状态；
- `POST /organizations/{organization_id}/members/{membership_id}/transfer-owner`：仅当前 owner 可执行；
- owner transfer 后原 owner 降级为 `admin`，目标 active membership 升级为 `owner`。

前端 API 类型继续与正式 Contract 对齐，未新增平行 API client、mapper 或状态机。

## 5. 验证要求

本地环境保持现有服务运行，不由测试脚本自动启动服务。测试数据全部由 Playwright API 流程和 deterministic reset 脚本生成，不手工填写测试信息。

### 5.1 重置 E2E 数据

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
uv run python scripts/test/e2e/00_reset_browser_e2e_database.py
```

预期：

```text
BROWSER_E2E_DATABASE_RESET_OK owner=browser_e2e_owner
```

### 5.2 targeted Browser E2E

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend
npm run test:e2e -- tests/e2e/organization-management.spec.ts
```

本轮修复提交后，需要重新执行上述命令确认 3 项均通过。本记录不将尚未重新执行的结果标记为通过。

### 5.3 targeted 通过后继续全量门禁

```powershell
npm test
npm run build
npm run test:gate
```

## 6. 版本与提交

- 本轮开始前检查远端 `main`，当前 `main` 为 `f55fa9b9f233b0e123e656061115b15c5343c1e2`。
- `frontend` 已以 fast-forward 方式同步到该 `main`，因为此前 organization E2E 修复提交已成为 `main` 的祖先；未使用 force update。
- 本轮修复将测试代码与本回归文档放入同一个原子提交，避免源代码与验收记录再次拆分。

## 7. 下一步

1. 用户本地重新执行 deterministic reset + organization-management targeted E2E。
2. 若 3 项通过，继续执行 `npm test`、`npm run build`、`npm run test:gate`。
3. 若仍失败，优先依据实际 trace / error-context 定位新的真实失败点，不通过增加 sleep 或延长 Toast 观察窗口掩盖时序问题。
4. organization management 稳定后回到项目当前主线 P1.1：Runtime Tab/按需加载、Agent 调试上下文、Workflow 生命周期与真实 Execution 联动。
