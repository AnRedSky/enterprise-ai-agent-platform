# Worker Service：AuditLog 历史 Execution ForeignKey 导致 Runtime 失败

## 1. 现象

独立 Worker Service 启动后消费历史 `WorkflowExecution` 时，Runtime 在状态转换阶段失败，并出现二次 `PendingRollbackError`。

根因日志：

```text
Foreign key associated with column 'audit_logs.execution_id' could not find table 'executions' with which to generate a foreign key to target column 'id'
```

## 2. 根因

早期可观测性领域使用 `executions` 表；当前 Workflow Runtime 已统一使用 `workflow_executions`。

数据库历史结构与 `AuditLog` 中的 `execution_id` 历史列仍需保留以读取旧审计数据，但当前代码不应继续把该列声明为指向已经退出当前领域模型的 `executions` 表的 ORM ForeignKey。

SQLAlchemy 在当前 Worker 真实持久化流程发生 `AuditLog` flush 时需要解析 ORM ForeignKey，发现 `executions` 已不在当前模型元数据中，于 flush 前后触发异常。随后 Workflow Execution 异常处理继续使用同一已回滚 Session，产生 `PendingRollbackError`，掩盖了原始模型映射错误。

## 3. 修复原则

- 保留 `audit_logs.execution_id` 历史列，保证历史数据兼容。
- 删除当前 ORM 层面对 `executions.id` 的 ForeignKey 声明。
- 当前 Workflow Execution 正式关联继续使用 `workflow_execution_id -> workflow_executions.id`。
- 不恢复已经退役的 `executions` 模型。
- 不新增兼容代理模型或旧入口。

## 4. 验证要求

必须依次执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_model_metadata_integrity.py
uv run pytest -q tests/unit/test_workflow_worker.py
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

其中真实 API Gate 必须在重新启动新的 Worker Service 后执行，不能使用修复前已经运行的旧 Worker 进程。
