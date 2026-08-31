# UI-04 Core Regression

## 目标

在七个真实页面完成 UI-04 公共状态迁移后，统一验证 `StatePanel` 五态、403 Permission、Error Retry、Empty 操作入口、Success 数据展示及未知状态边界，并清理 Vitest 测试环境中的组件解析 warning。

## 回归范围

- 公共组件：`src/components/ui/StatePanel.vue`
- 页面：DashboardOverview、KnowledgeWorkbench、ToolWorkbench，以及既有 UI-04 迁移页面的公共状态契约
- 状态：Loading / Empty / Error / Permission / Success
- 边界：未知业务状态必须显示 `未知状态（技术值）`，不得静默映射为已知状态

## 自动化覆盖

### StatePanel

- 五态均有独立渲染断言
- Error action emit
- Element Plus icon/button 在测试环境显式 stub

### Dashboard

- Loading
- Empty
- 403 Permission
- Error + Retry 后恢复 Success
- Success metrics/workspace
- 未知 execution status 原样进入中文未知状态提示
- `el-icon` 显式 stub，消除 Vue resolve warning

### Knowledge

- Loading
- Empty + 创建知识库入口
- 403 Permission
- Error + Retry 后恢复 Success
- Success workspace
- 未知 knowledge-base status 显式提示
- `el-icon` 显式 stub，消除 Vue resolve warning

### Tool

- Loading
- Empty + 创建工具入口
- 403 Permission
- Error + Retry 后恢复 Success
- Success workspace
- `el-icon` 已显式 stub

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

本轮 GitHub 远端操作仅具备源码与 Git 操作能力，没有本地 Node/Vitest 执行环境，因此不得把上述命令标记为远端已通过。用户此前提供的本地结果确认 Dashboard 5/5、Knowledge 5/5、StatePanel 6/6 已通过；本轮新增回归断言需要在本地按上述顺序重新执行。

## 已知限制

`StatePanel` 依赖 Element Plus icon 组件。页面测试使用显式 `el-icon` stub 解决 Vitest 的组件解析 warning；这不会改变生产环境 Element Plus 渲染。

## 完成条件

只有 targeted + full Vitest、build、test:gate、test:final 均实际通过后，UI-04 才可从“进行中”更新为“已完成”，随后进入 UI-05。
