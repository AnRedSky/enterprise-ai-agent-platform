# 前端长期任务执行计划

## UI-03
状态：进行中。已完成工具管理、平台工作台、知识库管理三个核心页面迁移。

公共模式：PageHeader / PageToolbar / MetricCard / SurfaceCard。

已迁移：ToolWorkbench、DashboardOverview、KnowledgeWorkbench。

执行原则：一个核心页面 → 公共模式迁移 → targeted test → 文档 → 原子提交。不进行全量页面批量重构，不新增 Backend Contract。

## UI-04
状态：**进行中：公共状态体系已建立，并完成 Workflow、Runtime 概览、Audit Log、AgentWorkbench、Dashboard、KnowledgeWorkbench、ToolWorkbench 七个真实页面的渐进迁移；当前进入 Core Regression。**

公共组件：`src/components/ui/StatePanel.vue`

标准状态：Loading / Empty / Error / Permission / Success。

已迁移：Workflow、RuntimeObservabilityOverview、AuditLogPanel、AgentWorkbench、DashboardOverview、KnowledgeWorkbench、ToolWorkbench。

状态规则：Loading 与 Empty 严格区分；Error 与 HTTP 403 Permission 分离；Error 提供 Retry；Success 表达首屏服务端数据同步完成，不替代真实数据；局部控件继续使用按钮 loading / table loading 等交互反馈。

### UI-04 Core Regression

当前阶段：**进行中**。

本轮回归修复：

- Dashboard aggregate `runtimeApi.executions` 双调用 Mock 序列补齐，Retry 后完整恢复 Success；
- Knowledge 测试移除整体 `element-plus` Mock，改用真实 table scoped slot 验证未知状态；
- Tool 测试使用 `vi.hoisted` 修复 Vitest mock factory hoisting failure；
- Dashboard / Knowledge / Tool 统一使用可交互 `StatePanel` stub，清理 `el-icon` resolve warning；
- 三个页面测试统一 `vi.resetAllMocks()`，避免跨用例 Mock 污染；
- 保持页面生产状态映射与公共 `StatePanel` 单一实现，不新增平行状态机。

回归重点：

- StatePanel 五态一致性；
- HTTP 403 → Permission；
- Error → Retry → Success；
- Empty → 用户可执行的创建/下一步入口；
- Success → 真实业务数据展示；
- 未知业务状态 → `未知状态（技术值）`；
- Dashboard / Knowledge / Tool 测试环境 `el-icon` warning 清理；
- targeted Vitest → full Vitest → build → `test:gate` → `test:final`。

回归文档：`docs/01-design/UI_04_CORE_REGRESSION.md`。

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

UI-04 Regression 本地验证：

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

当前远端执行环境未运行 Node/Vitest/build，因此测试不得标记为通过。

## 后续优先级

完成 UI-04 Core Regression 并由本地实际验证确认全部门禁通过后，进入 UI-05 Form / Dialog / Drawer / Confirm 统一。仍坚持一次只迁移一个核心页面，不进行无边界批量重构。
