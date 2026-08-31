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

## UI-04
状态：**进行中：公共状态组件基础能力已建立，尚未批量迁移业务页面。**

首轮基础设施：
- `src/components/ui/StatePanel.vue`：统一 Loading / Empty / Error / Permission / Success；
- `tests/components/StatePanel.test.ts`：覆盖五种状态及可恢复 Action；
- `docs/01-design/UI_04_STATE_SYSTEM.md`：记录状态语义、集成边界、测试及后续迁移规则；
- `src/main.ts`：注册 `ElIcon`，确保公共状态组件的图标依赖可运行。

状态体系原则：
- Loading 与 Empty 严格区分；
- Error 提供可恢复操作但不暴露内部错误；
- Permission 独立于 Error；
- Success 不能替代服务端数据刷新；
- 页面状态组件不承载业务 API、权限判断或领域状态机；
- 页面级状态优先使用 `StatePanel`，表格/容器级加载可继续使用 `v-loading`；
- 每次只迁移一个核心页面。

下一步：选择一个高频治理页面，优先 Workflow / Runtime，将真实页面状态迁移到 `StatePanel`；完成 targeted test、文档后再提交，不进行全量替换。

本地验证：
```powershell
cd frontend
npm test -- tests/components/StatePanel.test.ts
npm test
npm run build
npm run test:gate
npm run test:final
```

当前远端执行环境未运行本地 Node/Vitest/build，因此测试不得标记为通过。
