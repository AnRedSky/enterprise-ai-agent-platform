# Agent UI-04 Permission Regression

## 1. 问题

本地 targeted Vitest 中，`AgentWorkbench UI-04 > separates chat context permission from chat context error` 失败：

- 期望：`chatContextState === "permission"`
- 实际：`chatContextState === "empty"`
- 失败点：`frontend/tests/views/AgentUI04.test.ts:73`

## 2. 根因

`AgentWorkbench.vue` 原有 `isPermissionError()` 通过 `JSON.stringify()` 后搜索 `403` / `forbidden` 判断权限错误。这种基于序列化文本的判断没有直接遵循正式 API 错误对象的结构化 `response.status` 字段，也无法稳定覆盖不同 HTTP client / 测试替身的错误形态。

前端页面状态必须基于后端真实 HTTP 状态，而不是依赖错误正文文本推断。

## 3. 修复

将权限错误识别收敛为结构化优先判断：

1. `error.response.status === 403`
2. `error.status === 403`
3. `error.code === "FORBIDDEN"`
4. 最后仅对 `message` 字符串兼容识别 `403` / `forbidden`

该逻辑继续被 Agent 列表、版本、生效版本和调试上下文共用，避免新增平行错误状态判断。

## 4. 验证要求

本地依赖已安装时，在 `frontend` 目录执行：

```powershell
npm run test:unit -- --run tests/views/AgentUI04.test.ts
npm run test:unit -- --run tests/views/AgentUI04.test.ts tests/views/AuditLogUI04.test.ts tests/views/Dashboard.test.ts tests/views/Tools.test.ts tests/views/OperationsConsole.test.ts
npm run test:unit
npm run build
npm run test:gate
```

本次 GitHub 操作未执行本地 Node/Vitest 进程，因此不能将上述命令标记为已通过；用户提供的原始结果为 20/21 tests passed，1 failed，修复后需要按顺序重新执行。

## 5. 已知非阻断问题

用户反馈中还存在 Element Plus 测试桩未覆盖产生的 Vue warning：`el-icon`、`el-tag`、`v-loading`。这些 warning 不属于本次权限状态回归的根因，不应与本修复混入同一个原子提交；后续可作为测试基础设施清理任务单独处理。
