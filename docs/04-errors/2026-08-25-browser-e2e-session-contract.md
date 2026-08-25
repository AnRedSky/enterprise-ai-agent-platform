# 2026-08-25 Browser E2E Session、Element Plus 交互与持久化等待 Contract 问题

## 1. 现象

### 1.1 Browser Session 问题

在 `c7c2a58` 修复正式前端路由后，开发者重新执行 Workflow Trigger Browser E2E，测试仍未进入 Workflow Trigger 页面：

```text
Locator: getByText('Workflow Trigger Governance', { exact: true })
Expected: visible
Timeout: 5000ms
```

测试已经使用正式路由 `/workflows/triggers`，但页面标题不可见。

### 1.2 Element Plus Select 点击问题

在 `4ce5423` 建立真实 Browser Session 后，开发者再次执行 Workflow Trigger Browser E2E，页面已经进入正式 Workflow Trigger 页面，但在选择 Trigger 类型时失败：

```text
Locator: getByLabel('类型')
Error: locator.click: Test timeout of 60000ms exceeded
```

Playwright 已解析到 Element Plus `el-select` 内部的 readonly input，但实际点击时被 `el-select__suffix` 下的 SVG 拦截，因此不能稳定打开下拉框。

### 1.3 Trigger 持久化实体等待问题

在 `14625163` 的 Select Contract 修复后，开发者重新执行 Browser E2E，页面已经完成 Trigger 创建并进入后续调度状态验证，但测试在读取持久化 Trigger ID 时失败：

```text
TypeError: Cannot read properties of undefined (reading 'id')

trigger_id: persistedCreatedTrigger.id
```

失败发生在：

```text
const persistedCreatedTrigger = await expect.poll(...).toMatchObject(...);
```

随后把 `persistedCreatedTrigger` 当作实际 Trigger 实体读取 `id`。

## 2. 根因

### 2.1 Browser Session

Frontend Router 对非公开路由执行 `isAuthenticated()` 检查。正式前端 Session 存储在浏览器 `localStorage`：

- `enterprise_agent_access_token`
- `enterprise_agent_roles`
- `enterprise_agent_user_id`

E2E 虽然通过 Playwright `APIRequestContext` 完成真实注册、登录并取得 access token，但之前只在 API 请求中使用 `Authorization` Header，没有把真实登录结果建立到 Browser Context 的正式 Session 存储中。

因此 `page.goto("/workflows/triggers")` 触发认证守卫并进入登录页。

### 2.2 Element Plus Select

`getByLabel("类型")` 对 Element Plus `el-select` 命中的是内部 readonly input，而不是 Select 组件的可点击根节点。Element Plus 的 suffix SVG 在浏览器事件命中测试中会拦截该 input 的 pointer event。

该问题属于 **E2E 测试定位 Contract 不稳定**，不是生产 Trigger 类型选择业务逻辑错误。

### 2.3 Playwright Poll 断言返回值误用

`expect.poll()` 用于建立轮询断言；`toMatchObject()` 是断言操作，不是返回被断言对象的 API。将：

```text
const value = await expect.poll(...).toMatchObject(...)
```

当作实体读取会得到 `undefined`，因此后续 `value.id` 必然失败。

本问题属于 **测试实现错误**，不是 Backend Trigger Persistence Contract 或 Scheduler Runtime Contract 失败。

## 3. 修复边界

已完成：

1. `frontend/tests/e2e/workflow-trigger-governance.spec.ts` 使用真实 `/auth/login` 返回的 `access_token`、`roles`、`user_id` 初始化浏览器 `localStorage`，使 Browser Session 与正式前端认证 Contract 一致。
2. `frontend/src/views/workflow-triggers/index.vue` 为 Trigger 类型 `el-select` 增加稳定的 `data-testid="workflow-trigger-type-select"` test hook。
3. E2E 使用 `getByTestId("workflow-trigger-type-select")` 点击 Select 根节点，不再依赖 Element Plus 内部 readonly input。
4. 新增 `waitForPersistedTrigger` 自动化等待函数，通过真实 Backend HTTP 轮询 PostgreSQL 持久化结果；只有找到目标 Trigger 才返回实体。
5. 后续 Scheduler 状态查询继续使用真实持久化 Trigger 的 `id`，不构造 fixture 或复制生产算法。

本次没有：

- 修改生产 Router；
- 增加旧路由兼容入口；
- 修改 Backend Auth Contract；
- 修改 Scheduler Runtime、Repository、Migration 或调度算法；
- 使用 `force`、`evaluate` 等方式绕过真实 UI 行为；
- 放宽页面业务断言掩盖失败；
- 使用 JSON fixture 或进程内假数据替代真实 PostgreSQL 持久化。

## 4. 验证要求

修复后必须由开发者重新执行 Workflow Trigger Browser Gate；只有本地实际输出通过后，才能更新 Acceptance / Project Status 为通过。

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

建议完整验证顺序：

```powershell
# 1. Frontend Regression Gate
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1

# 2. Workflow Trigger Browser E2E
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

如果继续失败，应优先检查真实浏览器 Session、Frontend API Base URL、Backend HTTP Auth Contract、页面 test hook、真实 PostgreSQL 持久化可见性和 Scheduler 状态 Contract，而不是修改业务断言来规避失败。
