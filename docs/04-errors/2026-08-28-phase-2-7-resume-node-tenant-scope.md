# 2026-08-28 Phase 2.7 Resume Node tenant scope 回归

## 现象

本地执行 `uv run pytest -q -W error tests/unit` 时，Durable Resume Runtime / DAG Resume 相关测试出现：

```text
AttributeError: type object 'WorkflowNodeExecution' has no attribute 'tenant_id'
```

同时 DAG Resume tenant-scope Contract 测试原先要求直接在 `WorkflowNodeExecution` 上过滤 `tenant_id`，与实际 ORM schema 不一致。

## 根因

`workflow_node_executions` 表没有独立 `tenant_id` 字段。NodeExecution 的 tenant boundary 必须由所属 `WorkflowExecution` 提供。此前部分 Resume Runtime 查询直接引用不存在的 `WorkflowNodeExecution.tenant_id`；DAG Resume 查询虽然已移除不存在字段，但没有继续显式校验关联 Execution 的 tenant，无法 fail-closed 地阻止异常 `resume_of_execution_id` 数据造成跨 tenant Node fact 读取。

## 修复

### Durable Resume Runtime

`backend/app/services/workflow_worker/resume_runtime.py` 的 NodeExecution 查询统一通过：

```text
WorkflowNodeExecution.execution_id
        ↓ JOIN
WorkflowExecution.id
        ↓ WHERE
WorkflowExecution.tenant_id == execution.tenant_id
```

覆盖：

- 持久化 Node retry count；
- 单 Node Resume retry policy；
- 线性 Resume 已完成 Node 过滤；
- 全 Node 完成后的 Resume terminalization 判断。

### DAG Resume Runtime

`backend/app/runtime/workflow/dag_runtime.py` 的 `_load_completed_resume_nodes()` 同样通过 `WorkflowExecution` JOIN 显式限定 tenant：

```text
NodeExecution.execution_id IN {current, source}
AND WorkflowExecution.tenant_id = current.tenant_id
AND NodeExecution.status = completed
```

这样 tenant boundary 与数据模型一致，并覆盖 current / source 两条 Resume lineage。

不新增 `WorkflowNodeExecution.tenant_id` 字段，不复制 tenant 数据，也不增加兼容入口。

## 测试 Contract 调整

- `test_workflow_execution_idempotency.py` 与 `test_workflow_execution_governance.py` 中用于 Execution 创建 / Retry 的 Workflow fixture 已同步为当前非空 DAG edges Contract。
- `test_workflow_dag_runtime_initialization.py` 的 tenant-scope 断言同步为 `workflow_executions.tenant_id`，测试正式的 JOIN boundary，而不是不存在的 NodeExecution 字段。

## 验证状态

代码已提交到 `main`，但当前环境无法替代开发者本地 Python/uv/PostgreSQL 环境执行完整测试，因此本记录不宣称本地 Gate 已通过。

下一步必须由开发者在同步后的 `main` 上重新执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_durable_resume_runtime.py tests/unit/test_workflow_execution_idempotency.py tests/unit/test_workflow_execution_governance.py tests/unit/test_workflow_dag_runtime_initialization.py
uv run pytest -q -W error tests/unit
```

只有实际执行结果才允许更新 `PROJECT_STATUS.md` 为新的通过/失败统计。
