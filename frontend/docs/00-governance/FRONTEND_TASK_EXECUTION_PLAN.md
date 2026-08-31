# 前端长期任务执行计划

## UI-03
状态：进行中。已完成工具管理、平台工作台、知识库管理三个核心页面迁移。

公共模式：PageHeader / PageToolbar / MetricCard / SurfaceCard。

已迁移：
- views/tools/components/ToolWorkbench.vue
- views/dashboard/components/DashboardOverview.vue
- views/knowledge/components/KnowledgeWorkbench.vue

已补充测试：
- tests/views/Tools.test.ts
- tests/views/DashboardUI03.test.ts
- tests/views/KnowledgeUI03.test.ts

已补充设计记录：
- docs/01-design/UI_03_DASHBOARD_MIGRATION.md
- docs/01-design/UI_03_KNOWLEDGE_MIGRATION.md

执行原则：一个核心页面 → 公共模式迁移 → targeted test → 文档 → 原子提交。当前不进行全量页面批量重构，不新增 Backend Contract。

下一轮继续从核心业务页面中选择一个页面进行迁移，优先考虑 Workflow / Runtime 等高频治理页面。

本地验证：
```powershell
cd frontend
npm test -- tests/views/KnowledgeUI03.test.ts
npm test -- tests/views/DashboardUI03.test.ts
npm test -- tests/views/Tools.test.ts
npm test
npm run build
npm run test:gate
npm run test:final
```

当前远端执行环境未运行本地 Node/Vitest/build，因此测试不得标记为通过。