# Phase 1.5-F：Workflow Execution 可执行闭环

## 本项目标

在已有 Workflow Registry / Version / Publish / Governance / Execution 查询能力之上，补齐管理端的最小可执行闭环：

```text
Workflow
  ↓
Published Version
  ↓
Create Execution
  ↓
Run Execution
  ↓
Execution Status / Nodes
  ↓
Audit / Trace
```

本项不引入可视化 DAG 编辑器，也不改变现有 Workflow Runtime 的状态机设计。

## 实施内容

### Frontend API

新增：

- `workflowApi.createExecution(workflowId, inputData)`
- `workflowApi.runExecution(executionId)`

### Workflow Governance 页面

Execution 页签增加：

- JSON Input 编辑区
- 创建 Execution
- 运行 Execution
- 已创建 Execution ID 自动回填
- 运行后刷新节点状态
- 保留已有 Execution ID 查询能力

创建 Execution 前要求当前 Workflow 存在已发布 Version；实际版本选择仍由后端根据 `published_version_id` 决定，避免前端绕过发布治理直接执行草稿版本。

### Contract / UI Tests

- 后端锁定 Workflow Execution run route contract。
- 前端 API 测试覆盖 create/run。
- Workflow Governance view 测试覆盖创建并运行 Execution。

## 职责隔离

本项没有新增测试入口，也没有改变现有 `tests / scripts` 目录职责。

测试继续使用既有 Vitest / pytest 入口；开发与迁移脚本继续保持独立。

## 验收标准

```powershell
cd backend
uv run pytest -q

cd ..\frontend
npm test
npm run build
```

重点确认：

- Workflow Execution create/run API contract 正常。
- 已发布 Workflow 可以从管理端创建 Execution。
- Execution 可以从 pending 进入 Runtime 执行。
- 执行结果及 Node 状态可以回显。
- 原有 Audit / Trace 能力不受影响。
- 前端构建保持无既有 Rollup warning。

## 后续边界

本项完成后暂不继续人工细分 vendor chunk，也不立即实现 DAG 可视化编辑器。下一项应继续围绕 Workflow Runtime / Governance 的真实业务能力推进，并优先补足端到端可验证闭环。
