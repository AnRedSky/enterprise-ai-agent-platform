# 2026-08-31 前端回归阻塞修复记录

## 1. 背景

本轮开发首先核对 `main` 与 `frontend` 的同步状态；此前已存在 main → frontend 同步提交。本轮开发者反馈显示前端回归门禁存在 7 个失败文件、11 个失败测试以及 4 个未处理 Promise rejection，主要集中在 UI-03 / UI-04 状态契约与测试 harness。

## 2. 根因与修复

### 2.1 Knowledge UI-03 Loading 首屏状态

`KnowledgeWorkbench` 的 `loading` 初始值为 `false`，而 `onMounted(loadBases)` 发生在 mount 生命周期之后，导致首个同步渲染周期进入 Empty。修复为初始 `loading = true`，请求完成后仍由 `finally` 归位。

### 2.2 Runtime UI-04 Loading 首屏状态

`RuntimeObservabilityOverview` 同样将 `loading` 初始值设为 `false`。修复为初始 `loading = true`，保持现有请求和状态计算逻辑不变。

### 2.3 Tool UI-03 状态契约测试漂移

测试仍要求旧的 `el-empty` DOM，而 `ToolWorkbench` 已迁移到公共 `StatePanel`。测试改为验证 `StatePanel` 的 `empty` 状态、标题和描述；管理员创建动作改为验证 `PageHeader` action slot 的可见文本，不绑定 Element Plus stub 内部 DOM。

### 2.4 Runtime Operations Audit Tab

测试直接修改 `wrapper.vm.activeTab`，依赖 Element Plus Tabs 内部状态同步，导致 Audit pane 未稳定进入测试上下文。测试改为定位 `Audit` tab 并触发 click，再执行下一 tick 后验证过滤器与审计数据。

### 2.5 Runtime / Audit UI-04 Unhandled Rejection

`it.each` 直接在测试参数定义阶段创建 `Promise.reject(...)`，Vitest 在测试消费前即捕获 unhandled rejection。修复为 Promise factory，在每个测试体内创建 rejected Promise 并立即交给 API mock。

### 2.6 Workflow Webhook Runtime E2E 严格定位冲突

开发者本地执行 `npm run test:e2e -- tests/e2e/workflow-webhook-runtime.spec.ts` 时，Webhook Runtime E2E 在生命周期工作台断言处失败。页面为同一工作流名称同时渲染了 `strong` 身份标题、`span` 元信息和表格单元格，`getByLabel("工作流生命周期工作台").getByText(workflow.name, { exact: true })` 因严格模式解析为 3 个元素而失败。

根因不是 Workflow 生命周期数据或深链 Contract，而是测试定位器只约束了文本，没有约束工作流身份区域的 DOM 语义。页面已经提供稳定的 `.workflow-identity strong` 身份标题，因此回归测试改为在工作流生命周期工作台内定位 `.workflow-identity strong`，并用 `toHaveText(..., { exact: true })` 验证真实工作流名称。

该修复不修改业务代码、API Contract 或生命周期状态机，只收敛 E2E 测试边界，避免通过 `.first()` 等顺序性选择器掩盖真实 DOM 歧义。

### 2.7 Runtime Correlations 深链未自动恢复关联事实

开发者继续执行 Webhook Runtime E2E 时，生命周期工作台断言已通过，但进入 `/runtime?tab=correlations&focus_type=execution&focus_id=<execution_id>...` 后，`Audit / Trace 关联` 标题可见，而 `Execution ID` 不存在。根因是 `RuntimeCorrelations` 已从 route query 初始化 `focusType` / `focusId`，但只在用户点击“查询关联”时调用 `query()`，没有在深链首次挂载时恢复关联事实。

该行为与前端准则要求的 Runtime 深链上下文恢复不一致，也导致真实用户从 Workflow、Webhook、Audit 或 Trace 深链进入关联工作台后必须重复点击查询。修复为在 `RuntimeCorrelations` 的 `onMounted` 阶段检测已有 `focusId`，直接复用现有 `query()` 和既有 API client 查询对应 durable facts；没有深链 ID 时仍保持原 Empty 状态，不增加额外请求。

### 2.8 Runtime Correlations 深链路由上下文同步

开发者在上述 `onMounted` 修复后再次执行同一 targeted E2E，`Execution ID` 仍未在 5 秒断言窗口内出现。进一步审查 `RuntimeWorkspaceTabs`、`RuntimeCorrelations` 与 Vue Router 生命周期后确认，关联工作台属于由 Runtime Tabs 管理的子视图，深链上下文本质上是 route-driven state；仅依赖一次 `onMounted` 无法覆盖组件实例复用或 route query 在挂载后完成同步的情况。

根因进一步收敛为 **Runtime Correlations 将 route query 当作一次性初始化数据，而不是持续的路由状态源**。修复改为监听 `focus_type`、`focus_id`、`execution_id` 三个关联上下文 query，并使用 `immediate: true` 首次同步。focus 发生变化时重置 Trace/Audit 分页与选中事实，再复用既有 `query()` 请求对应 durable facts；没有 focus ID 时清理结果并恢复 Empty 状态。

### 2.9 Runtime Correlations immediate watcher 首次水合条件遗漏

开发者再次执行同一 targeted E2E 后，失败位置仍是 `/runtime` 关联工作台中的 `Execution ID`，且此前的 route watcher 已经存在。重新核对 watcher 的实际执行条件后发现了更具体的根因：`watch(..., { immediate: true })` 首次回调执行时，`focusType` / `focusId` 已在 setup 阶段由同一 route query 初始化，因此 `focusChanged` 为 `false`；原实现又只在 `focusChanged` 为 `true` 时调用 `query()`，导致 **首次 immediate watcher 虽然执行，却没有发起 hydration 请求**。

本次修复保留 route watcher 作为唯一路由状态源，但把“是否需要水合”与“focus 是否发生变化”解耦：当当前 `result` 尚未存在，或者 focus 发生变化时，只要存在有效 `focusId` 就复用现有 `query()`；focus 变化仍负责重置 Trace/Audit 分页和选中事实；没有 focus ID 且确实发生 focus 变化时清理结果并恢复 Empty 状态。

该修复直接对应本地反馈中的“标题存在、Execution ID 不存在”现象，不修改 E2E 断言、不等待任意固定时间、不新增 API 或 mapper，也不改变 Backend Contract。现有 `workflow-webhook-runtime.spec.ts` 的 `Execution ID` 断言继续作为真实深链 hydration 回归门禁。

### 2.10 WorkflowLifecycle Operator Action Contract 收口

Backend Phase 2.10-II 已将 Workflow Execution / Trigger 的运维操作统一收口到 `Runtime Operator Action Governance`：Execution 支持 `run / cancel / retry / resume`，Trigger 支持 `enable / disable / delete / invoke`；高风险操作要求 `confirm=true`，Retry / Invoke 要求 `Idempotency-Key`，成功结果通过统一 `result` durable resource 返回，并由治理层负责租户边界、状态冲突、幂等与 Operator Audit。

前端原 `workflowApi` 仍暴露稳定的 `runExecution / cancelExecution / retryExecution / resumeExecution / invokeTrigger / deleteTrigger` 调用边界，因此本轮未在页面复制第二套状态机或新增平行 client；仅将这些方法的 HTTP 路径切换到 canonical Operator Action Contract，并在 API client 层解包 `result`，保持现有 WorkflowLifecycle 组件调用方式不变。Retry / Invoke 在调用方未提供 key 时生成一次性幂等键；高风险动作明确发送 `confirm=true`。

### 2.11 WorkflowLifecycle 第二阶段：Availability Contract 消费

本轮将前端最终操作资格切换到 Backend Operator Action Availability Contract。Workflow Execution 详情加载时，前端请求 `/runtime/operator-actions/workflow-executions/{execution_id}`，以 `actions[]` 中的 `allowed` 作为 Run / Cancel / Retry / Resume 唯一展示条件，并同时保留 `reason_code`、`requires_confirmation`、`requires_idempotency_key` 等治理元数据。

Resume 不再由 `failed` 状态直接推出可用；Backend Availability 内部执行 Durable Checkpoint Recovery Assessment，前端只接受后端返回的 `allowed` / `reason_code`，从而尊重 `CHECKPOINT_NOT_ELIGIBLE` 等真实 checkpoint eligibility。

Trigger 同步消费 `/runtime/operator-actions/workflow-triggers/{trigger_id}` Availability，manual Invoke 与 Delete 均不再单独复制后端状态资格。Scheduler 仍保持只读。

403 明确映射 Permission；409 根据后端 detail 区分状态冲突与 Idempotency / replay 结果冲突。Retry / Invoke 的成功结果直接使用 `result` Durable Resource；Retry lineage 通过 `retry_of_execution_id` 展示，Resume 通过 `resume_checkpoint_sequence` 展示。每次成功操作后重新拉取 Execution、Availability 与 Trigger 状态，Backend refresh 继续作为最终事实源。

Operator Action → Result Resource → Audit → Execution → Trace 的完整追踪链没有在前端复制：页面只展示后端返回的 Result Resource 和真实 Durable ID，并继续通过 Runtime / Trace / Audit 深链进入统一观测入口。

## 3. 变更范围

本轮 WorkflowLifecycle Availability 收口范围：

- `frontend/src/api/workflows.ts`
- `frontend/src/views/workflows/WorkflowLifecycle.vue`
- `frontend/tests/api/workflows.test.ts`
- `frontend/tests/views/WorkflowLifecycle.test.ts`
- `frontend/docs/00-governance/FRONTEND_TASK_EXECUTION_PLAN.md`
- `frontend/docs/07-testing-regression/2026-08-31-frontend-regression-followup.md`

此前深链修复范围仍包括：

- `frontend/src/views/runtime/components/RuntimeCorrelations.vue`
- `frontend/tests/e2e/workflow-webhook-runtime.spec.ts`

## 4. 验证状态

此前用户已提供最新 Windows 本地验证结果：

```text
npm run test:e2e -- tests/e2e/workflow-webhook-runtime.spec.ts
1 passed (8.0s)
```

用户同时反馈 `npm test`、`npm run build`、`npm run test:gate` 均执行并通过；由于完整日志较长未提供，本记录只保存用户确认的通过事实，不虚构具体测试数量、耗时或 gate 明细。

本轮新增 Availability targeted test 已写入 API 与 WorkflowLifecycle view tests，但当前远端工具环境没有执行开发者 Windows Node/Vitest。因此本轮新改动必须由用户本地 targeted regression 验证，不能将未执行命令标记为通过。

建议 targeted：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend
npm run test:unit -- --run tests/api/workflows.test.ts tests/views/WorkflowLifecycle.test.ts
npm run test:e2e -- tests/e2e/workflow-webhook-runtime.spec.ts
```

随后再执行完整门禁：

```powershell
npm test
npm run build
npm run test:gate
```

## 5. 完成判定

WorkflowLifecycle 第二阶段代码、targeted tests、任务台账和回归文档已按同一原子交付准备完成；**最终验收状态待用户本地 targeted regression 验证**。在用户确认新 targeted tests 通过前，不标记本轮为最终回归通过。
