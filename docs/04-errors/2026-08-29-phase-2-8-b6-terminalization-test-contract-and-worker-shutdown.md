# Phase 2.8 B6：终态 Frontier 测试契约与 Worker shutdown 错误记录

## 1. 发现时间

2026-08-29

## 2. 影响范围

- Phase 2.8 B6 Delegation Multi-Worker Runtime
- `WorkflowExecutionService` terminalization boundary
- Backend default regression
- Worker 进程退出时 SQLAlchemy AsyncEngine / asyncpg 连接释放

## 3. 现象

最新 main 基线 `9e26d181` 的本地 B6 Gate 在 Backend default regression 阶段出现 5 个单元测试失败：

1. `test_terminal_transition_rejects_active_frontier`
2. `test_terminal_transition_allows_execution_without_active_frontier`
3. `test_pending_execution_can_start_and_complete`
4. `test_terminal_transition_atomically_clears_worker_ownership[completed]`
5. `test_terminal_transition_atomically_clears_worker_ownership[failed]`

失败分别表现为 `_assert_no_active_frontiers_for_terminal_transition()` 参数数量不匹配，以及测试替身没有实现新的 SQLAlchemy `Result.scalars().all()` 查询契约。

直接运行 `uv run python run_worker.py` 停止 Worker 时还出现 asyncpg / asyncio `CancelledError` 连接关闭日志。

## 4. 根因

### 4.1 Terminalization 单元测试契约滞后

B6 terminalization 修复把 Frontier 检查从“查询单个标识”收紧为：在同一事务内锁定 Execution 对应的活动 Frontier 集合，并允许当前 Worker 唯一、running、fencing generation 一致且 lease 有效的 Frontier 与 Execution 一起进入终态。

因此正式方法现在需要统一的 `now` 与 `target_status`，并使用 SQLAlchemy ORM Result 的 `scalars().all()` 读取 Frontier 集合。旧测试仍按旧私有方法签名调用，测试替身仍只提供 `scalar_one_or_none()`，导致回归失败。这不是生产 SQLAlchemy 查询本身的错误，而是测试替身没有随正式事务契约同步。

### 4.2 Worker shutdown 的 cancellation 生命周期

Worker 退出时主协程可能已经处于 cancelling 状态。若 AsyncEngine `dispose()` 第一次被取消后重新抛出 `CancelledError`，asyncpg 连接关闭会在事件循环仍处于退出边界时继续收到 cancellation，形成连接池异常日志。

## 5. 修复

### 5.1 测试契约同步

更新以下测试，使其与当前正式 terminalization contract 一致：

- `backend/tests/unit/test_execution_terminalization_boundary.py`
  - 使用 `now` / `target_status` 调用正式方法；
  - 测试替身提供 `scalar_one_or_none()` 与 `scalars().all()`；
  - 增加“当前 Worker 唯一有效 running Frontier 可原子终态化”的边界覆盖。
- `backend/tests/unit/test_workflow_execution_state_machine.py`
  - `_db()` 测试结果补齐 Frontier 集合查询契约。
- `backend/tests/unit/test_workflow_execution_terminal_ownership.py`
  - `_Result` 补齐 `scalars().all()`。

### 5.2 Worker shutdown 修复

`backend/app/entrypoints/worker.py` 的 `_dispose_database_engine()` 在收到 cancellation 时先消费当前 Task 的 pending cancellation，再完整执行一次 `engine.dispose()`；清理成功后不再重新抛出已处理的 shutdown cancellation，避免正常 Worker 停止被误报为 asyncpg 连接关闭异常。

## 6. 验证要求

代码修复后必须由开发者本地实际执行 B6 Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\06_delegation_multi_worker_runtime_gate.ps1
```

在新的本地结果产生前，不将 B6 标记为通过，也不提前进入 Phase 2.9。

## 7. 相关设计约束

- 不创建第二套 Execution / Frontier / Delegation 状态机。
- 不使用 Mock 替代 Real API + PostgreSQL 验收链路。
- Gate 自动生成测试用户、Token、UUID 与测试数据，不要求手工填写测试信息。
- Gate 不自动启动、重启或停止 PostgreSQL、Redis、Backend 等服务，只验证本地前置服务状态。
