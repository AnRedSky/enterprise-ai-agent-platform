# UI-04 状态测试 Harness 回归记录 — 2026-09-01

## 1. 基线

本轮先确认最新 `main` 并将其快进同步到历史 `frontend` 分支。当前 `main` / `frontend` 基线均为 `3da6d0be38fddf7d3f93a5b0449ba28609e52897`（`fix(operations): align correlation internal page types`）。前端继续遵循现行准则：Backend Contract → API Types → View / Component → Vitest → Real API / E2E；状态页面必须覆盖 Loading / Empty / Error / Success / Permission。

用户本地回归反馈集中在 Dashboard / Agent / AuditLog / Tool，以及既有 UI-04 状态测试：

- Agent UI-04：21 个 targeted 测试中仅 1 个失败；失败用例在点击“对话调试”后直接从 DOM 查询 StatePanel `permission`，未稳定表达组件的异步 `chatContextState` 状态契约。
- AgentWorkbench 生产代码已经由 `openChat()` 设置 `chatVisible=true` 并调用 `loadChatContext(agent.id)`；`loadChatContext()` 将后端 403 映射为 `chatContextState="permission"`，因此本次不修改生产状态机。
- Dashboard / AuditLog / Tool 等测试仍可能输出 Element Plus `el-icon` / `v-loading` warning；这些 warning 属于测试 Harness 覆盖不足，不改变当前生产组件实现或本轮失败判定。

## 2. 根因与决策

### 2.1 Agent 对话调试 Permission 回归断言

`AgentWorkbench` 的对话调试状态是异步 API 请求驱动的组件状态：点击“对话调试”后先进入 loading，再由 `getPublishedVersion()` 的结果决定 `success` / `empty` / `permission` / `error`。直接依赖 `StatePanel` 是否已经出现在测试 DOM，会同时耦合 Element Plus Dialog stub 的可见性语义、Vue 异步渲染时序和状态组件 DOM 结构。

决策：回归测试以 `chatContextState` 作为一等状态契约，使用 `vi.waitFor()` 等待异步状态稳定，再验证 API 参数和用户可见 Permission 文案。生产页面状态机保持不变。

### 2.2 测试 Harness 边界

Dialog stub 继续只在 `modelValue=true` 时渲染 slot，并显式提供 `el-icon` 与 `loading` directive stub。这样保持测试与真实 Element Plus 可见性语义一致，同时避免通过修改业务组件来迎合测试。

## 3. 本轮修复

提交：`test: harden Agent UI-04 permission contract`

- `AgentUI04.test.ts`：将对话调试 Permission 断言从 DOM 直接查询改为等待 `chatContextState === "permission"`。
- 增加 `getPublishedVersion("a1")` 调用断言，确保点击入口仍绑定真实 Agent ID。
- 保留“无权加载调试配置”用户可见文案断言。
- 未新增 API client、mapper、状态枚举或业务逻辑；未修改 `AgentWorkbench.vue`。

## 4. 验证状态

用户本地反馈基线：5 个 targeted test 文件、21 个测试，20 个通过、1 个失败。失败定位为 Agent UI-04 异步状态回归断言，不是 Backend Contract 失败。

本轮远程操作环境不能直接执行用户 Windows 工作树中的 npm，因此不能把修复后的测试标记为已通过。请在本地执行：

```powershell
npm run test:unit -- --run `
  tests/views/AgentUI04.test.ts `
  tests/views/AuditLogUI04.test.ts `
  tests/views/Dashboard.test.ts `
  tests/views/Tools.test.ts `
  tests/views/OperationsConsole.test.ts
```

targeted 全部通过后继续按项目准则执行：

```powershell
npm test
npm run build
npm run test:gate
```

测试数据继续由 Vitest mock 自动生成，不启动服务、不手工填写业务数据、不使用 `npx` 临时下载测试框架。

## 5. 下一步

targeted UI-04 回归全部通过后，继续 P1.1 主线：Runtime Tab / 按需加载、Agent 调试上下文、Workflow 生命周期与真实 Execution 联动。避免重复实现公共状态模式，也不要为了消除测试 warning 修改生产组件。