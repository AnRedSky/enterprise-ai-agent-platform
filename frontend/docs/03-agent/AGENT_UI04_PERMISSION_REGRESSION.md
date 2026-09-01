# Agent UI-04 Permission Regression

## 1. 问题

本地 targeted/full Vitest 反馈暴露两个独立问题：

1. `AgentWorkbench UI-04 > separates chat context permission from chat context error`
   - 期望：`chatContextState === "permission"`
   - 实际：`chatContextState === "empty"`
   - 失败点：`frontend/tests/views/AgentUI04.test.ts:76`
2. `AgentWorkbench lifecycle > hides raw HTTP and backend error text from the user-facing error area`
   - 期望：`智能体列表加载失败，请刷新后重试。`
   - 实际：`智能体列表加载失败，请刷新后重试`
   - 失败点：`frontend/tests/views/Agents.test.ts:28`

最新本地结果：`45` 个测试文件中 `43` 个通过，`203` 个测试中 `201` 个通过，剩余上述 2 个失败。

## 2. 根因

调试上下文需要把请求失败与空数据严格分开。`getPublishedVersion()` 的权限拒绝必须进入 `permission`，不能因为初始状态或空的 `publishedVersion` 暴露 `empty`。

同时，Agent 列表的用户可见错误文案已经由测试契约固定为统一中文文案，并要求包含中文句号；后端 HTTP/Provider 原始错误不得直接展示。

## 3. 修复

本轮修复保持两个边界独立：

1. `loadChatContext()` 在请求开始时显式进入 `loading`。
2. 捕获异常后优先进行权限判定，再明确设置 `permission` 或 `error`。
3. `isPermissionError()` 结构化识别 `response.status`、`status`、`response.data.status`，兼容数值/字符串 `403`。
4. 同时识别 `code`、`response.data.code` 的 `FORBIDDEN` / `403`，并保留消息文本作为最后兼容路径。
5. Permission 分支使用用户可见文本 `无权加载调试配置`。
6. Agent 列表加载失败统一使用 `智能体列表加载失败，请刷新后重试。`，不暴露 HTTP 或 provider 原始错误。
7. 不新增第二套 Agent 状态机，不改变后端 API Contract，不重复实现公共状态组件。

## 4. 测试验证

本地 `frontend` 目录执行：

```powershell
npm run test:unit -- --run tests/views/AgentUI04.test.ts
npm run test:unit -- --run tests/views/Agents.test.ts
npm run test:unit
npm run build
npm run test:gate
```

当前用户反馈的全量结果为：

```text
Test Files  2 failed | 43 passed (45)
Tests       2 failed | 201 passed (203)
```

因此 UI-04 及 Agent lifecycle 当前仍不能标记为通过。修复后必须重新执行 targeted test，再执行全量 test、build、test:gate；未实际执行的命令不得标记为通过。

## 5. 独立测试环境问题

此前 `Tools.test.ts` 出现 `el-icon` 与 `loading` directive warning，但测试本身通过。该问题属于测试组件 stub / 测试基础设施边界，不与本次 Agent Permission 或错误文案修复混合。

## 6. 原子性边界

本次代码提交只修改 Agent Workbench 的错误分类与用户可见错误文案契约；本文件同步记录该修复及验证状态。UI-05 不在本次范围内。
