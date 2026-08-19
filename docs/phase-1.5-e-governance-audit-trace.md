# Phase 1.5-E：Governance / Audit / Trace

## 1. 目标

在 1.5-D Workflow Runtime 基础上建立 Workflow Execution 的治理闭环：关键生命周期动作产生不可变 AuditLog，节点与 Execution 状态变化形成可查询 Trace，并保持 tenant / owner / admin 隔离。

本阶段遵循平台 Governance Layer、Trace Collector 和版本可追溯原则。

## 2. 本阶段范围

### 2.1 Audit

Workflow Execution 生命周期写入 `audit_logs`：

- `workflow.execution.created`
- `workflow.execution.run`
- `workflow.execution.completed`
- `workflow.execution.failed`
- `workflow.execution.cancelled`

Audit 记录包含：tenant、workflow、workflow version、workflow execution、actor、status、error code 和 metadata。

Workflow Audit 不复用既有 Agent Runtime 的 `execution_id` 外键，而使用独立 `workflow_execution_id`，避免两套 Execution 模型 UUID 语义混淆。

### 2.2 Trace

新增 `workflow_trace_events`：

- execution.created
- execution.state_changed
- node.state_changed

每条 Trace 包含 tenant、workflow、version、execution、node、actor、trace_id、status、data 和错误信息。

### 2.3 Query API

新增：

```text
GET /api/v1/runtime/executions/{execution_id}/trace
```

Audit 查询增强：

```text
GET /api/v1/runtime/audit-logs
  ?workflow_id=<uuid>
  &workflow_execution_id=<uuid>
```

owner 只能查看自己 Workflow 的 Audit / Trace；admin 可跨 owner 查看，但仍受 tenant scope 约束。

## 3. 数据库

新增 Migration：

```text
0017_workflow_governance_audit_trace
```

变更：

- `audit_logs.tenant_id`
- `audit_logs.workflow_id`
- `audit_logs.workflow_version_id`
- `audit_logs.workflow_execution_id`
- `workflow_trace_events`

## 4. 测试门禁

Backend：

```powershell
cd backend
uv run pytest -q
uv run alembic upgrade head
uv run alembic current
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_phase_1_5_e_workflow_governance_validation.ps1
```

Backend 验证脚本只执行 Backend migration / pytest，不调用 frontend npm 测试。

Frontend 测试必须独立执行。

## 5. 已发生错误与修复

### 5.1 测试夹具缺少 `created_by`

1.5-E 在 `WorkflowExecutionService.transition()` 中接入 Governance Trace 后，旧状态机单元测试的 `SimpleNamespace` Execution 夹具未包含真实 Domain Contract 所需的 `created_by`，导致 full regression 出现 2 个 `AttributeError`。

修复方式：补齐 `backend/tests/test_workflow_execution_state_machine.py` 中的 `created_by=uuid4()`，保持测试夹具与真实 `WorkflowExecution` contract 一致；不在生产代码中添加针对测试对象的降级访问。

详细错误知识库记录：

```text
docs/error-tracking/003-workflow-execution-governance-test-fixture-created-by.md
```

### 5.2 测试夹具继续缺少 tenant / workflow / version 上下文

补齐 `created_by` 后，开发者再次执行 Backend full regression，仍出现 2 个失败：

```text
AttributeError: 'types.SimpleNamespace' object has no attribute 'tenant_id'
```

失败发生在 `WorkflowGovernanceService.trace()` 创建 `WorkflowTraceEvent` 时。Governance Trace 同时要求：

- `tenant_id`
- `workflow_id`
- `workflow_version_id`
- `created_by`
- `id`

本次修复将状态机测试中的重复 `SimpleNamespace` 统一收敛为 `_execution()` 工厂，并补齐上述上下文。生产代码不增加针对测试夹具的降级逻辑。

详细错误知识库记录：

```text
docs/error-tracking/004-workflow-execution-governance-test-fixture-tenant-context.md
```

## 6. 验收标准

1. Workflow 创建会生成 Audit 与 Trace。
2. Execution / Node 状态变化会生成 Trace。
3. Execution terminal state 会生成对应 Audit。
4. owner 无法读取其他 owner 的 Workflow Trace / Audit。
5. admin 可以读取跨 owner Workflow Trace / Audit。
6. Audit 使用 `workflow_execution_id`，不污染既有 Agent Runtime `execution_id` 语义。
7. Migration 实际升级到 0017 head。
8. Backend 全量 pytest 通过且无未解释 warning。
9. 实际验收结果写回 `docs/PROJECT_STATUS.md` 后才允许进入 1.5-F。

## 7. 明确边界

本阶段不实现：

- OpenTelemetry exporter
- Prometheus / Grafana
- MQ / Worker
- Cost dashboard
- Compliance policy engine
- Vue Governance UI
- Workflow UI
