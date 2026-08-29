# Frontend Phase 2.9 后端契约对齐与 Workflow Execution 优化

## 1. 变更基线

- 远端基线：`main`
- 基线提交：`8e1af7300711482c0ccb66219a256dc274a82f07`
- 后端当前阶段：Phase 2.9 Enterprise Integration / Event Infrastructure
- 后端当前切片：2.9-A Event Contract 已实现，2.9-B Durable Event Persistence 尚未实现。

本次前端工作不提前实现 Event UI，也不虚构 Kafka、MQ、Event Bus 或 Durable Event API。原因是 2.9-A 只冻结领域 Event Contract，后端尚未提供对应持久化或 HTTP 查询/管理接口。

## 2. 后端契约检查结论

当前 Workflow Execution HTTP API 已提供：

- `GET /api/v1/workflows/{workflow_id}/executions`
- `POST /api/v1/workflows/{workflow_id}/executions`
- `POST /api/v1/workflows/executions/{execution_id}/run`
- `POST /api/v1/workflows/executions/{execution_id}/cancel`
- `POST /api/v1/workflows/executions/{execution_id}/retry`
- `POST /api/v1/workflows/executions/{execution_id}/resume`
- `GET /api/v1/workflows/executions/{execution_id}`
- `GET /api/v1/workflows/executions/{execution_id}/nodes`
- `GET /api/v1/workflows/executions/{execution_id}/trace`

其中 Execution 响应已经包含 Durable Resume lineage 字段：

- `resume_of_execution_id`
- `resume_checkpoint_sequence`

因此前端原实现存在两个明确缺口：

1. API 类型没有表达 Resume lineage 字段；
2. Workflow Execution 页面只支持单个 Execution 查询，没有使用后端正式的 Workflow Execution 列表接口，也没有暴露 Durable Resume 操作。

## 3. 本次实现

### 3.1 API Contract

`frontend/src/api/workflows.ts`：

- 为 `WorkflowExecution` 增加 `resume_of_execution_id` 与 `resume_checkpoint_sequence`；
- 新增 `workflowApi.listExecutions(workflowId)`，严格调用后端正式列表接口；
- 新增 `workflowApi.resumeExecution(executionId)`，严格调用后端正式 Resume HTTP API。

没有新增平行 endpoint，也没有复制后端 Runtime 规则。

### 3.2 Workflow Execution UI

`frontend/src/views/workflows/index.vue`：

- 选择 Workflow 后同时加载 Version 与持久化 Execution 列表；
- 展示 Execution ID、状态、Version、创建时间；
- 点击历史 Execution 直接加载详情和 Node 状态；
- 创建、运行、取消、Retry 后刷新持久化 Execution 列表；
- 当当前 Execution 存在 `resume_checkpoint_sequence` 且不处于 `pending/running` 状态时展示 Durable Resume；
- Resume 前明确显示 Checkpoint 序号；
- Resume 成功后展示新的 `resume_of_execution_id` 与 `resume_checkpoint_sequence`，保留 lineage 可追踪性。

前端只负责展示与调用，不自行推导 Checkpoint、状态机或恢复计划。

## 4. 测试实现

`frontend/tests/api/workflows.test.ts` 增加：

- Execution 列表 endpoint 调用断言；
- Durable Resume endpoint 调用断言。

`frontend/tests/views/Workflows.test.ts` 增加：

- Workflow 选择后加载持久化 Execution 列表；
- Durable Resume 从既有 Checkpoint lineage 创建新 Execution；
- Resume lineage 字段回填断言。

测试实现继续位于 `frontend/tests/`，没有将测试代码放入生产目录。

## 5. 验收与本地执行要求

项目开发准则规定 Frontend Gate 独立于 Backend Gate，且开发验收必须以本地实际执行结果为准。本次变更应在开发者本地执行：

```powershell
cd frontend
npm test
npm run build
```

正式 Frontend Regression Gate：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

需要真实后端联调时，应先启动 API Service，并使用真实登录 Token，再通过浏览器验证：

1. 登录后进入 `/workflows`；
2. 选择已有 Workflow；
3. 确认 Execution 列表来自后端持久化接口；
4. 选择历史 Execution，确认详情、Node 状态与 lineage 正常；
5. 对具有有效 Checkpoint 的非运行中 Execution 执行 Durable Resume；
6. 确认后端创建新的 pending Execution，且 `resume_of_execution_id` 指向源 Execution；
7. 运行新的 Resume Execution，确认状态与 Node 状态可继续通过既有接口查询；
8. 检查浏览器 Network，确认只调用正式 `/api/v1/workflows/...` Contract，没有额外前端自定义 endpoint。

## 6. 未执行事项说明

当前工作环境通过 GitHub Repository API 完成代码审阅与原子提交，无法启动用户本地 Windows/Node/Backend/PostgreSQL 环境。因此本次不能声称 `npm test`、生产构建或真实 HTTP/浏览器联调已经实际通过。

提交前应由具备本地环境的开发者按上述命令执行，并把实际通过/失败结果作为后续验收事实记录；禁止预填“通过”。

## 7. 后续边界

- 2.9-B Durable Event Persistence 完成后，再评估是否需要新增 Event Operations 前端能力；
- 2.9-C Reliable Delivery / 2.9-D Webhook Integration 完成前，不在前端虚构 Delivery 状态、重试队列或 Webhook 管理 Contract；
- 继续遵循 Backend Contract → Frontend API Types → Frontend UI → Frontend Gate → 联调的开发顺序。
