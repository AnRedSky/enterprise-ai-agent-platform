# UI-04 ToolWorkbench 状态迁移

## 范围

本轮仅迁移 `ToolWorkbench.vue` 的页面级 Loading / Empty / Error / Permission / Success，不修改 Tool API Contract，不改变创建、启停、绑定、解绑和执行接口。

## 状态映射

- Loading：工具与智能体首屏请求期间使用 `StatePanel.loading`。
- Empty：查询成功且工具为空，使用 `StatePanel.empty`，提供创建入口。
- Error：首屏请求失败且不是 403，使用 `StatePanel.error` 并提供 Retry。
- Permission：HTTP 403 独立映射为 `StatePanel.permission`，不展示可误导用户继续操作的工作台。
- Success：查询成功且存在工具时恢复原工具列表和操作工作台。

## 实现决策

1. 复用现有 `StatePanel`，不创建 Tool 专用状态组件。
2. 保留表格 `v-loading` 和创建、绑定、执行按钮的局部 loading；页面级状态只负责首屏数据可用性。
3. 保留现有 `listTools` / `listAgents` 请求组合，不新增平行 API client 或 mapper。
4. 403 仅根据 HTTP status 映射为 Permission；其他异常继续通过 `getToolUserError` 转换为用户可读错误。
5. Success 仅代表首屏数据已同步且至少存在一个工具，不创建额外的“成功提示”状态，避免覆盖真实业务数据。

## Targeted Test

新增 `tests/views/ToolUI04.test.ts`，覆盖：

- Loading
- Empty
- 403 Permission
- Recoverable Error
- Populated Success

测试中的 Element Plus 组件使用轻量 stub；`el-icon` 显式 stub，避免 StatePanel 在 Vitest 环境产生组件解析 warning。

## 验证

本次远端 GitHub 操作不具备本地 Node/Vitest 执行环境，因此不得把未实际执行的测试标记为通过。开发机应执行：

```powershell
cd frontend
npm test -- tests/views/ToolUI04.test.ts
npm test -- tests/views/DashboardUI04.test.ts
npm test -- tests/views/KnowledgeUI04.test.ts
npm test -- tests/components/StatePanel.test.ts
npm test
npm run build
npm run test:gate
npm run test:final
```

手动验证应覆盖：正常列表、空列表、403、网络错误重试，以及创建/启停/绑定/解绑/执行操作链路。
