# Organization Management E2E 回归记录 — 2026-09-04

## 1. 回归输入

本次修复基于用户本地 `frontend` 的真实 Playwright 反馈：

- `Organization management completes the real owner browser contract`：成员暂停成功后，5 秒内未捕获 `成员已暂停` 通知；成员状态断言尚未执行。
- `Organization browser governance enforces member and suspended-member boundaries`：通过。
- `Organization owner transfer exposes owner-only browser controls`：owner 登录后页面存在多个成员行，每个非 owner 行均可能渲染“转移所有权”，原测试使用 page 级 locator 触发 Playwright strict mode violation。

## 2. 根因

### 2.1 页面权限上下文

组织详情页的管理权限必须基于真实当前用户 membership，而不能从当前分页成员数组推导。当前 `frontend` 已通过独立 `currentMembership` 上下文和分页查找解决该问题；本次不重复实现。

### 2.2 E2E 通知是瞬时 UI 状态

Element Plus `ElMessage` 是短生命周期 DOM。仅使用 `expect(locator).toBeVisible()` 作为等待器，虽然在点击前建立等待，但如果浏览器事件循环在通知创建和销毁之间没有完成一次满足 locator 条件的采样，仍可能出现“element(s) not found”。

### 2.3 owner transfer locator 作用域过宽

组织 owner 可以向任意非 owner 成员转移所有权，因此详情页可能同时出现多个“转移所有权”按钮。page 级 `getByRole('button', { name: '转移所有权' })` 在多个匹配项存在时会触发 Playwright strict mode。测试应明确表达“owner 能看到该控制”，而不是假定全页只有一个按钮。

## 3. 本次修复方案

### E2E 通知捕获

`frontend/tests/e2e/organization-management.spec.ts` 的 `waitForMessage()` 改为在浏览器上下文中预先安装 `MutationObserver`：

- 监听 `.el-message` 的 DOM 创建、文本变化和子树变化；
- 在操作触发前建立观察器，避免依赖固定轮询窗口；
- 只接受同时满足 `.el-message`、目标业务文本和可见性的通知；
- 保留 5 秒超时，并在超时后给出明确的测试错误；
- 不修改生产 `ElMessage` duration，不通过增加 sleep 掩盖时序问题。

### owner transfer 控件

owner-only browser contract 保持业务语义不变：

- 原 owner 登录后断言“转移所有权”控件数量为 `0`；
- 新 owner 登录后断言 page 级 locator 的第一个匹配项可见；
- 不假定页面只存在一个目标成员，因此避免 strict mode 假设；
- owner transfer API 仍使用真实 membership ID，未修改后端权限规则。

## 4. Contract 对齐

后端正式 Organization Contract：

- `POST /auth/register`：新用户加入默认 Organization，初始 membership 为 `active/member`；
- `GET /organizations`：按用户 active membership 返回 Organization；
- `GET /organizations/{organization_id}/members?offset=&limit=`：分页返回真实 membership；
- `POST /organizations/{organization_id}/members/{membership_id}/transfer-owner`：仅当前 owner 可执行；
- owner transfer 后原 owner 降级为 `admin`，目标 active membership 升级为 `owner`。

本次未修改后端 Organization、membership、权限或 owner transfer 业务规则。

## 5. 验证要求

本地环境保持现有服务运行，不由测试脚本自动启动服务。测试数据全部由 Playwright API 脚本生成。

先执行 deterministic Browser E2E 数据重置：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
uv run python scripts/test/e2e/00_reset_browser_e2e_database.py
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

## 6. 当前状态

- `frontend` 当前分支已与最新 `main` 同步到 `8885308f10685f9b571a2df11c7b19149a29f738`，因此本轮无需重复创建 main→frontend 合并提交。
- 页面 `currentMembership` 权限上下文修复已存在，不重复实现。
- 本次提交仅修复 organization management E2E 的瞬时通知捕获和 owner-transfer locator strict mode。
- 用户提供的本地结果 `1 passed / 2 failed` 仍作为修复前证据；在用户本地重新执行前，不标记 targeted E2E 为通过。
- 本地 targeted E2E 通过后再执行全量 Vitest、build 和 regression gate；未实际执行的结果不得记录为通过。