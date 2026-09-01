# Agent UI-04 Permission Regression

## 1. 问题

本地 targeted Vitest 中，`AgentWorkbench UI-04 > separates chat context permission from chat context error` 失败：

- 期望：`chatContextState === "permission"`
- 实际：`chatContextState === "empty"`
- 失败点：`frontend/tests/views/AgentUI04.test.ts:76`

## 2. 根因

调试上下文加载存在两个独立的状态来源：请求状态 `loading/success/error/permission` 与 `publishedVersion` 数据是否为空。原实现只在请求成功后依据 `publishedVersion` 是否存在决定 `success/empty`，而权限失败路径需要稳定地把结构化权限错误映射为 `permission`，不能让默认的 `empty` 状态继续暴露。

同时，权限错误识别需要优先使用 HTTP client 提供的结构化状态字段，而不是依赖错误正文文本推断。

## 3. 修复

本次仅修复 Agent UI-04 调试上下文状态边界：

1. `loadChatContext()` 在请求开始时显式进入 `loading`，避免默认 `empty` 状态参与异步竞态。
2. 捕获错误后先计算权限判定，并明确设置 `permission` 或 `error`。
3. 权限错误优先识别 `response.status === 403`、`status === 403`，兼容字符串形式 `"403"` 以及 `code === "FORBIDDEN"` / `"403"`。
4. 权限分支使用明确的用户可见文本 `无权加载调试配置`，避免把权限拒绝误报为普通加载失败。
5. 不新增第二套 Agent 状态机；列表、版本、生效版本和调试上下文继续复用 `isPermissionError()`。

## 4. 验证要求

本地依赖已安装时，在 `frontend` 目录执行：

```powershell
npm run test:unit -- --run tests/views/AgentUI04.test.ts
npm run test:unit -- --run tests/views/AgentUI04.test.ts tests/views/AuditLogUI04.test.ts tests/views/Dashboard.test.ts tests/views/Tools.test.ts tests/views/OperationsConsole.test.ts
npm run test:unit
npm run build
npm run test:gate
```

本次 GitHub 操作未执行本地 Node/Vitest 进程，因此不能将上述命令标记为已通过；用户提供的原始结果为 4 个测试文件通过、20/21 tests passed、1 failed。修复提交后必须按上述顺序重新执行，并以实际终端结果作为验收事实。

## 5. 原子性边界

本修复只处理 UI-04 调试上下文 Permission/Empty 状态边界，不修改 Agent API Contract、不引入新的公共状态组件，也不提前推进 UI-05。

Element Plus 测试桩产生的非阻断 warning 不属于本次修复范围，应在独立测试基础设施任务中处理。
