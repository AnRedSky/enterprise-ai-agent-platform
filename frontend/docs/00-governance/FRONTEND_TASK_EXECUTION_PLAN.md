# 前端长期任务执行计划

## UI-03
状态：进行中。已完成工具管理、平台工作台、知识库管理三个核心页面迁移，并开始 Workflow 生命周期工作台公共模式收敛。

公共模式：PageHeader / PageToolbar / MetricCard / SurfaceCard。

已迁移：ToolWorkbench、DashboardOverview、KnowledgeWorkbench；本轮新增 WorkflowLifecycle 第一批公共容器迁移。

## UI-04
状态：**Core Regression 已完成用户本地 targeted 验证，进入 UI-05。**

公共组件：`src/components/ui/StatePanel.vue`

标准状态：Loading / Empty / Error / Permission / Success。

已迁移：Workflow、RuntimeObservabilityOverview、AuditLogPanel、AgentWorkbench、DashboardOverview、KnowledgeWorkbench、ToolWorkbench；本轮继续收敛 WorkflowLifecycle。

### UI-04 Core Regression

本轮已完成 Agent UI-04 Permission 回归。用户本地最新反馈中 `tests/utils/agentContextState.test.ts` 8/8 通过；随后 `AgentUI04.test.ts` 已通过。此前剩余失败根因是测试环境 `el-button` stub 同时触发 fallthrough click 与 `$emit('click')`，导致 `getPublishedVersion` 被调用两次；修复为声明 `emits: ['click']` 后消除重复事件。

## UI-05 Form / Dialog / Drawer / Confirm

状态：**进行中：ToolWorkbench 第一、二批迁移已实现；WorkflowLifecycle 第二个核心页面已开始公共模式迁移；RuntimeCorrelations 已完成 Durable Fact focused-record 定位。**

原则：一个核心页面 → 公共模式迁移 → targeted test → 文档 → 原子提交。

### ToolWorkbench

- 公共 `src/components/ui/ConfirmDialog.vue` 已接入停用、启用和解绑。
- 创建 Dialog 已完成名称必填、`input_schema` JSON 对象校验、提交 loading、成功关闭/重置、失败保留输入和响应式宽度。
- 用户本地 `Tools.test.ts` 8/8 通过，`ConfirmDialog.test.ts` 3/3 通过；合计 11/11 通过。
- 本轮本地失败已定位为测试夹具与 Element Plus 表格事件/渲染契约不一致，生产代码未被用于绕过测试。
- 设计记录：`docs/01-design/UI_05_TOOL_FORM_DIALOG_MIGRATION.md`。

### 第二个核心页面：WorkflowLifecycle

- 使用公共 `PageHeader`、`SurfaceCard`、`StatePanel`，统一页面标题、内容容器和 Loading / Empty / Error / Permission 状态。
- 保留真实 Workflow / Version / Trigger / Scheduler / Execution 关联和 Runtime 深链。
- 增加针对公共模式和页面状态契约的 targeted regression tests。
- 设计记录：`docs/01-design/UI_05_WORKFLOW_LIFECYCLE_MIGRATION.md`。

### RuntimeCorrelations Durable Fact 定位

- Runtime correlation Response 新增 `focused_traces` / `focused_audit` 后，前端 API 类型已对齐该 Contract。
- Trace focus 优先消费后端 `focused_traces`，即使目标 Trace 不在当前分页 `traces.items` 中也能展示具体 Durable Fact。
- Audit focus 优先消费后端 `focused_audit`，即使目标 Audit 不在当前分页 `audits.items` 中也能展示具体 Durable Fact。
- Trace / Audit 进入 Runtime correlation 或返回 WorkflowLifecycle 时均优先使用 focused Durable Fact 自身携带的真实 Execution / Workflow / Version ID。
- 列表分页保持原有 page/page_size 语义，不扩大分页、不复制后端关系查询、不通过时间、排序、索引或字符串推导关系。
- Regression 覆盖“目标不在当前分页但存在 focused fact”的 Trace / Audit 深链定位场景。
- 设计记录：`docs/01-design/UI_05_WORKFLOW_LIFECYCLE_EXECUTION_OPERATIONS.md`。

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

## 本地验证

ToolWorkbench：

```powershell
cd frontend
npm run test:unit -- --run tests/views/Tools.test.ts
npm run test:unit -- --run tests/components/ConfirmDialog.test.ts tests/views/Tools.test.ts
```

WorkflowLifecycle / RuntimeCorrelations：

```powershell
cd frontend
npm run test:unit -- --run tests/views/WorkflowLifecycle.test.ts tests/views/RuntimeCorrelations.test.ts
npm run build
npm run test:unit
npm run test:gate
```

远端执行环境不运行 Node/Vitest/build，因此未实际执行的门禁不得标记为通过。

## 下一任务

继续 UI-05 主线：以 RuntimeCorrelations 的 focused Durable Fact 定位为基础，完成一次用户本地 targeted regression + build 验证；确认稳定后继续 WorkflowLifecycle 的 Form / Dialog / Drawer / Confirm 交互收敛，再选择下一个核心页面。不进行跨页面大规模重构，不新增平行 API client、状态机或 Dialog。