# 前端长期任务执行计划

## UI-03
状态：进行中。已完成工具管理、平台工作台、知识库管理三个核心页面迁移。

公共模式：PageHeader / PageToolbar / MetricCard / SurfaceCard。

已迁移：ToolWorkbench、DashboardOverview、KnowledgeWorkbench。

## UI-04
状态：**Core Regression 已完成用户本地 targeted 验证，进入 UI-05。**

公共组件：`src/components/ui/StatePanel.vue`

标准状态：Loading / Empty / Error / Permission / Success。

已迁移：Workflow、RuntimeObservabilityOverview、AuditLogPanel、AgentWorkbench、DashboardOverview、KnowledgeWorkbench、ToolWorkbench。

### UI-04 Core Regression

本轮已完成 Agent UI-04 Permission 回归。用户本地最新反馈中 `tests/utils/agentContextState.test.ts` 8/8 通过；随后 `AgentUI04.test.ts` 已通过。此前剩余失败根因是测试环境 `el-button` stub 同时触发 fallthrough click 与 `$emit('click')`，导致 `getPublishedVersion` 被调用两次；修复为声明 `emits: ['click']` 后消除重复事件。

## UI-05 Form / Dialog / Drawer / Confirm

状态：**进行中：ToolWorkbench 第一批迁移已实现。**

原则：一个核心页面 → 公共模式迁移 → targeted test → 文档 → 原子提交。

### 第一批：ToolWorkbench Confirm

- 新增公共 `src/components/ui/ConfirmDialog.vue`。
- ToolWorkbench 的停用、启用和解绑操作统一经过公共确认组件。
- ConfirmDialog 只负责展示、loading、confirm/cancel 事件，不包含 Tool 领域规则。
- 创建、绑定、执行三个现有 Dialog 暂不整体重构，避免一次性改变成熟业务链路。
- 高风险操作继续由后端权限和正式 API 最终裁决。
- 新增 `tests/components/ConfirmDialog.test.ts`；更新 `tests/views/Tools.test.ts` 验证危险操作进入公共确认模式。
- 设计记录：`docs/01-design/UI_05_TOOL_FORM_DIALOG_MIGRATION.md`。

### 下一批

继续 ToolWorkbench 的创建 Dialog 表单统一：校验、提交 loading、成功关闭、失败保留输入和响应式宽度；完成 targeted/full 门禁后再选择第二个核心页面迁移。

## 固定执行流程

```text
同步 main
  → 读取真实源码/API Contract
  → 一个核心页面
  → 公共模式迁移
  → targeted test
  → 设计文档
  → 原子提交
  → 用户本地完整验证
```

UI-05 本地验证：

```powershell
cd frontend
npm run test:unit -- --run tests/components/ConfirmDialog.test.ts tests/views/Tools.test.ts
npm test
npm run build
npm run test:gate
npm run test:final
```

远端执行环境不运行 Node/Vitest/build，因此未实际执行的门禁不得标记为通过。
