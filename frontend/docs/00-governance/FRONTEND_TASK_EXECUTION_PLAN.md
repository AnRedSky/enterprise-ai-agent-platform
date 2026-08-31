# 前端长期任务执行计划

## UI-03
状态：进行中。已完成工具管理、平台工作台、知识库管理三个核心页面迁移。

公共模式：PageHeader / PageToolbar / MetricCard / SurfaceCard。

已迁移：ToolWorkbench、DashboardOverview、KnowledgeWorkbench。

执行原则：一个核心页面 → 公共模式迁移 → targeted test → 文档 → 原子提交。不进行全量页面批量重构，不新增 Backend Contract。

## UI-04
状态：**进行中：公共状态体系已建立，并完成 Workflow、Runtime 概览、Audit Log、AgentWorkbench 四个真实页面渐进迁移；本轮补齐 Dashboard。**

公共组件：`src/components/ui/StatePanel.vue`

标准状态：Loading / Empty / Error / Permission / Success。

已迁移：
- Workflow 页面
- RuntimeObservabilityOverview
- AuditLogPanel
- AgentWorkbench
- DashboardOverview

本轮 Dashboard：
- `views/dashboard/components/DashboardOverview.vue`
- `tests/views/DashboardUI04.test.ts`
- `docs/01-design/UI_04_DASHBOARD_MIGRATION.md`

状态规则：
- Loading 与 Empty 严格区分；
- Error 与 HTTP 403 Permission 分离；
- Error 提供 Retry；
- Success 表达服务端同步完成，不替代真实数据；
- 聚合 Dashboard 的 Success 直接展示真实指标，不用 Success 面板覆盖业务内容；
- 页面级状态使用 StatePanel，局部控件继续使用按钮 loading / v-loading 等交互反馈。

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
npm test -- tests/views/DashboardUI04.test.ts
npm test -- tests/components/StatePanel.test.ts
npm run build
npm run test:gate
npm run test:final
```

当前远端执行环境未运行 Node/Vitest/build，因此测试不得标记为通过。

## 后续优先级

继续补齐 UI-04 高频核心页面中的 Knowledge / Tool；完成核心页面覆盖后执行 UI-04 Regression，再进入 UI-05 Form / Dialog / Drawer / Confirm。