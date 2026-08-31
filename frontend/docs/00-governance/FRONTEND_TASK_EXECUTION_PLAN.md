# 前端长期任务执行计划

## UI-03
状态：进行中。已完成工具管理、平台工作台、知识库管理三个核心页面迁移。

公共模式：PageHeader / PageToolbar / MetricCard / SurfaceCard。

已迁移：ToolWorkbench、DashboardOverview、KnowledgeWorkbench。

执行原则：一个核心页面 → 公共模式迁移 → targeted test → 文档 → 原子提交。不进行全量页面批量重构，不新增 Backend Contract。

## UI-04
状态：**进行中：公共状态体系已建立，并完成 Workflow、Runtime 概览、Audit Log、AgentWorkbench 四个真实页面的渐进迁移。**

公共组件：`src/components/ui/StatePanel.vue`

标准状态：Loading / Empty / Error / Permission / Success。

已迁移：
- Workflow 页面
- RuntimeObservabilityOverview
- AuditLogPanel
- AgentWorkbench

本轮 AgentWorkbench：
- `views/agents/components/AgentWorkbench.vue`
- `tests/views/AgentUI04.test.ts`
- `docs/01-design/UI_04_AGENT_MIGRATION.md`

状态规则：
- Loading 与 Empty 严格区分；
- Error 与 HTTP 403 Permission 分离；
- Error 提供 Retry；
- Success 表达服务端同步完成，不替代真实数据；
- Chat streaming / completed / failed / cancelled 保留为领域状态，不被页面 StatePanel 粗暴替换；
- 页面级状态使用 StatePanel，局部控件继续使用按钮 loading 等交互反馈。

## 固定执行流程

```text
一个核心页面
  → 读取真实源码/API Contract
  → 状态迁移
  → targeted test
  → 设计文档
  → 单一原子提交
  → 本地完整验证
```

本地验证：

```powershell
cd frontend
npm test -- tests/views/AgentUI04.test.ts
npm test -- tests/components/StatePanel.test.ts
npm run build
npm run test:gate
npm run test:final
```

当前远端执行环境未运行 Node/Vitest/build，因此测试不得标记为通过。

## 后续优先级

UI-04 下一步继续选择一个核心业务页面；不批量修改其他页面。完成 UI-04 核心页面覆盖后，再进入 UI-05 Form / Dialog / Drawer / Confirm 统一。