# 2026-09-03 Scheduler Runtime 集成测试清理锁竞争

## 1. 现象

Backend Regression 在 `test_scheduler_runtime_persists_misfire_execution_and_governance_chain` 中偶发失败。

已观察到两类数据库错误：

- PostgreSQL `40P01 deadlock detected`，发生在按 tenant 删除 `workflow_executions` 时；
- PostgreSQL 外键冲突，删除 `workflow_versions` 时仍存在 `workflow_executions.workflow_version_id` 引用。

本地完整回归随后可出现 `1058 passed, 80 deselected`，说明问题具有并发竞态特征，而不是确定性的业务断言错误。

## 2. 根因

该集成测试允许本地共享 PostgreSQL 中已经运行的 Worker/Runtime 消费测试创建的 Durable Frontier。

原清理逻辑虽然按照子表到父表的顺序删除，并对 `40P01` 做有限重试，但仍存在以下竞态：

1. 清理事务删除本测试已有的 Workflow Execution；
2. 并发 Worker 事务仍可能持有或重新建立 `WorkflowExecution -> WorkflowVersion` 的外键引用；
3. 清理事务随后删除 `WorkflowVersion` 时，可能等待并发事务，形成锁环；
4. 死锁事务回滚后，另一次清理尝试可能在 Worker 新提交的 Execution 上触发外键冲突。

因此仅重试 deadlock 不能建立可靠的清理隔离。

## 3. 修复

`backend/tests/integration/test_workflow_scheduler_runtime.py` 的 `_cleanup()` 在清理事务开始时首先：

```sql
SELECT id
FROM workflow_versions
WHERE id = :workflow_version_id
FOR UPDATE
```

随后继续按照子表到父表的顺序删除测试事实。

原因：PostgreSQL 外键检查需要对被引用父行取得 `KEY SHARE` 锁，而 `FOR UPDATE` 与该锁冲突。先取得 WorkflowVersion 的排他行锁，可以让清理事务等待已经进行的引用事务完成，同时阻止新的事务在清理事务期间建立该外键引用，从而消除“删除 Execution 后又重新产生引用”的窗口。

保留 `40P01` 有限重试作为异常并发下的最后保护，但不再把 deadlock 重试当作主要正确性机制。

## 4. 测试边界

本修复只调整测试隔离/清理，不修改 Scheduler、Worker、Execution 或数据库外键业务语义。

测试仍然：

- 自动生成 tenant/user/workflow/version/trigger/schedule/Execution 等 ID；
- 不要求开发者手工填写测试数据；
- 不自动启动、停止、重启 API、Worker、Scheduler、PostgreSQL 或 Redis；
- 继续使用真实 PostgreSQL；
- 保留 Scheduler Runtime 的真实状态机与 Audit/Trace 断言。

## 5. 本地验证要求

修复提交后必须由开发者在本地执行：

```powershell
cd backend
uv run pytest -q tests/integration/test_workflow_scheduler_runtime.py
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

如果 PostgreSQL/Worker/Scheduler 等外部依赖缺失，遵循项目 Gate 规则输出 `[NOT EXECUTED]`，不得由 Gate 自动启动受保护服务。
