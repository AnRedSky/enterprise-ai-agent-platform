# Scheduler Runtime 集成测试清理死锁

## 现象

Backend Regression 在 `tests/integration/test_workflow_scheduler_runtime.py::test_scheduler_runtime_persists_misfire_execution_and_governance_chain` 的 `finally` 清理阶段失败：PostgreSQL 返回 `DeadlockDetectedError`（SQLSTATE `40P01`）。当时结果为 `1 failed, 1057 passed, 80 deselected`。

## 根因

该测试会在共享 PostgreSQL 中创建 ScheduleSlot、WorkflowExecution 和 Durable Frontier。`tick_once()` 返回后，本地断言已经完成，但如果开发环境存在实际 Worker，Worker 仍可能正在推进同一测试租户的 Execution/Frontier。

清理事务随后按外键依赖顺序删除 Frontier、ScheduleSlot、Execution；Runtime 事务则可能同时持有 Execution/Frontier 的行锁。两个事务以不同时间取得相关锁后互相等待，形成 PostgreSQL 锁环。

这不是业务状态机错误，也不能通过降低断言、关闭 Worker 或跳过数据库集成测试解决。测试必须能够与合法的后台 Runtime 并发共存，并保证失败后的测试数据仍能可靠清理。

## 修复

`backend/tests/integration/test_workflow_scheduler_runtime.py` 的 `_cleanup()` 增加有限、明确的 PostgreSQL deadlock 重试：

- 仅识别 SQLSTATE `40P01`；
- 每次死锁立即回滚当前清理事务，由下一次尝试重新建立事务；
- 使用递增短等待，最多 10 次；
- 非死锁数据库错误立即继续抛出，不吞掉真实错误；
- 清理成功立即返回。

这样保留真实 Runtime/Worker 并发语义，同时避免后台短事务与测试 teardown 的瞬时锁环导致整个 Backend Regression 失败。

## 边界

- 不修改 Scheduler/Worker 生产状态机。
- 不关闭、停止、重启或自动启动任何服务。
- 不放宽 Scheduler Runtime 的业务断言。
- 不使用固定测试 ID；测试仍为每次运行生成新的 tenant/workflow/trigger/schedule/执行事实。
- 不将 deadlock 作为“通过”条件；只有完整清理事务成功才视为 teardown 成功。

## 验证要求

本地必须重新执行 Backend Regression：

```powershell
cd backend
uv run pytest -q
```

随后重新执行 Backend Release Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

测试结果以本地实际输出为准，不预填通过状态。
