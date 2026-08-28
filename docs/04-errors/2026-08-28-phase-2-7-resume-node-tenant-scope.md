# 2026-08-28 Phase 2.7 Resume Node tenant scope 回归

## 现象

本地执行 `uv run pytest -q -W error tests/unit` 时，Durable Resume Runtime 相关测试集中出现：

```text
AttributeError: type object 'WorkflowNodeExecution' has no attribute 'tenant_id'
```

## 根因

`workflow_node_executions` 表没有独立 `tenant_id` 字段。Resume Runtime 原实现直接引用 `WorkflowNodeExecution.tenant_id`，与当前 ORM schema 不一致；同时该写法没有表达“NodeExecution 的 tenant boundary 由所属 Workflow Execution 确定”的正式数据模型。

## 修复

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

不新增 `WorkflowNodeExecution.tenant_id` 字段，不复制 tenant 数据，也不增加兼容入口。

## 测试 Contract 调整

`test_workflow_execution_idempotency.py` 与 `test_workflow_execution_governance.py` 中用于 Execution 创建 / Retry 的 Workflow fixture 已同步为当前非空 DAG edges Contract，避免测试 double 继续构造已被正式 Validator 拒绝的空 edges 定义。

## 验证状态

代码已提交到 `main`，但当前环境无法替代开发者本地 Python/uv/PostgreSQL 环境执行完整测试，因此本记录不宣称本地 Gate 已通过。

下一步必须由开发者在同步后的 `main` 上重新执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_durable_resume_runtime.py tests/unit/test_workflow_execution_idempotency.py tests/unit/test_workflow_execution_governance.py
uv run pytest -q -W error tests/unit
```

只有实际执行结果才允许更新 `PROJECT_STATUS.md` 为新的通过/失败统计。
