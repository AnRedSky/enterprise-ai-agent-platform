# UI-04 Core Regression

## 目标

在七个真实页面完成 UI-04 公共状态迁移后，统一验证 `StatePanel` 五态、403 Permission、Error Retry、Empty 操作入口、Success 数据展示及未知状态边界，并清理 Vitest 测试环境中的组件解析 warning。

## 本轮修复

本轮针对用户本地回归反馈，根因定位为**测试装配与 Mock 生命周期问题**，不是页面状态机重复实现：

1. Dashboard 的 aggregate API 一次加载实际调用 `runtimeApi.executions` 两次（最近执行 + failed 总数）；回归 Mock 必须为两个调用分别提供返回值，Retry 场景同样保持完整调用序列。
2. Knowledge 测试原先整体 Mock `element-plus`，导致 `StatePanel` 的按钮行为和页面组件装配不稳定；同时页面测试依赖真实表格 scoped slot 才能验证未知知识库状态。现改为使用真实 Element Plus table/column/tag，并仅对非目标交互组件做 stub。
3. Tool 测试存在 Vitest `vi.mock` hoisting 问题，`listTools/listAgents` 不能使用 mock factory 外部的顶层变量；现统一通过 `vi.hoisted` 创建 Mock。
4. Dashboard / Knowledge / Tool 页面测试统一使用可交互的 `StatePanel` stub，显式验证状态 class、Action 按钮和恢复路径，避免 `el-icon` resolve warning 污染回归输出。
5. 三个页面测试统一使用 `vi.resetAllMocks()`，避免前一个用例的实现或一次性返回值影响后续用例。

## 回归范围

- 公共组件：`src/components/ui/StatePanel.vue`
- 页面：DashboardOverview、KnowledgeWorkbench、ToolWorkbench，以及既有 UI-04 迁移页面的公共状态契约
- 状态：Loading / Empty / Error / Permission / Success
- 边界：未知业务状态必须显示 `未知状态（技术值）`，不得静默映射为已知状态

## 自动化覆盖

### StatePanel

- 五态均有独立渲染断言
- Error action emit
- Element Plus icon/button 在组件测试中显式 stub

### Dashboard

- Loading
- Empty
- 403 Permission
- Error + Retry 后恢复 Success
- Success metrics/workspace
- 未知 execution status 原样进入中文未知状态提示
- aggregate executions 双调用契约在成功与 Retry 路径均被覆盖
- 页面状态测试不再依赖未解析的 `el-icon`

### Knowledge

- Loading
- Empty + 创建知识库入口
- 403 Permission
- Error + Retry 后恢复 Success
- Success workspace
- 未知 knowledge-base status 显式提示
- 使用真实 table scoped slot 验证状态文案
- 页面状态测试不再通过整体 Mock `element-plus` 产生组件解析副作用

### Tool

- Loading
- Empty + 创建工具入口
- 403 Permission
- Error + Retry 后恢复 Success
- Success workspace
- Mock factory 使用 `vi.hoisted`，消除 Vitest hoisting failure
- 页面状态测试不再依赖未解析的 `el-icon`

## 验证命令

```powershell
cd frontend
npm test -- tests/views/DashboardUI04.test.ts
npm test -- tests/views/KnowledgeUI04.test.ts
npm test -- tests/views/ToolUI04.test.ts
npm test -- tests/components/StatePanel.test.ts
npm test
npm run build
npm run test:gate
npm run test:final
```

## 当前事实

远端 Git 操作环境没有本地 Node/Vitest 执行能力，因此本轮**未将任何测试、Build、Gate 或 Final Gate 标记为已通过**。用户此前提供的本地结果确认 `StatePanel` 6/6 已通过；Dashboard 与 Knowledge 的旧测试结果已不再代表当前修复后的回归结果。

本轮修改后必须在用户本地重新执行上述 targeted → full → build → gate → final 顺序，并以实际命令退出码作为完成依据。

## 已知限制

- GitHub 远端连接可用于源码审查和提交，但当前执行环境不能安装/运行 Node 依赖，因此无法替代用户本地 Vitest/build 验证。
- E2E / Real API 不由 `test:gate` 或 `test:final` 自动执行，仍按项目既定验收文档单独执行。

## 完成条件

只有 targeted + full Vitest、build、`test:gate`、`test:final` 均实际通过后，UI-04 才可从“进行中”更新为“已完成”，随后进入 UI-05。
