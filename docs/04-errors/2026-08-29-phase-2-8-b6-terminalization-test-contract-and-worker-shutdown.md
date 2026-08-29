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

在上述测试契约修复后，开发者重新执行 B6 Gate，当前 main 基线进一步暴露 1 个 Worker shutdown 单元测试失败：

`test_dispose_database_engine_retries_after_cancellation_and_preserves_signal`

该测试验证首次 `AsyncEngine.dispose()` 收到 cancellation 后必须先完成第二次 dispose，再恢复原始取消语义；旧实现虽然完成了第二次 dispose，却把 cancellation 静默吞掉，因此测试未抛出预期的 `asyncio.CancelledError`。

## 4. 根因

### 4.1 Terminalization 单元测试契约滞后

B6 terminalization 修复把 Frontier 检查从“查询单个标识”收紧为：在同一事务内锁定 Execution 对应的活动 Frontier 集合，并允许当前 Worker 唯一、running、fencing generation 一致且 lease 有效的 Frontier 与 Execution 一起进入终态。

因此正式方法现在需要统一的 `now` 与 `target_status`，并使用 SQLAlchemy ORM Result 的 `scalars().all()` 读取 Frontier 集合。旧测试仍按旧私有方法签名调用，测试替身仍只提供 `scalar_one_or_none()`，导致回归失败。这不是生产 SQLAlchemy 查询本身的错误，而是测试替身没有随正式事务契约同步。

### 4.2 Worker shutdown 的 cancellation 生命周期

Worker 退出时主协程可能已经处于 cancelling 状态。若 AsyncEngine `dispose()` 第一次被取消后立即结束，asyncpg 连接关闭可能在事件循环仍处于退出边界时继续收到 cancellation，形成连接池异常日志。因此必须先消费当前 Task 的 pending cancellation，确保第二次 dispose 在稳定的事件循环上下文中完成。

### 4.3 取消语义被错误吞掉

上一轮 shutdown 修复只解决了“第二次 dispose 必须完成”，却同时将第一次收到的 cancellation 视为可忽略信号。这样会改变调用者可观察到的生命周期语义：上层 Worker 无法知道停止请求曾经发生，且现有单元测试明确要求恢复 `CancelledError`。

正确边界是：**资源清理优先于 cancellation，但资源清理成功后必须恢复 cancellation 语义**。因此实现需要记录 cancellation，使用 `Task.uncancel()` 临时清除 pending cancellation 完成第二次 dispose，最后重新抛出 `asyncio.CancelledError`。

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

`backend/app/entrypoints/worker.py` 的 `_dispose_database_engine()` 在收到 cancellation 时先消费当前 Task 的 pending cancellation，再完整执行一次 `engine.dispose()`；第二次 dispose 成功后重新抛出 `asyncio.CancelledError`，恢复调用者可观察的 shutdown cancellation 语义，同时避免连接池清理被同一个 cancellation 中断。

对应的 B6 targeted unit gate 已补入 `tests/unit/test_worker_entrypoint.py`，避免该生命周期契约只能在 Backend default regression 阶段才被发现。

## 6. 验证要求

代码修复后必须由开发者本地实际执行 B6 Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\06_delegation_multi_worker_runtime_gate.ps1
```

Gate 自动生成测试用户、Token、UUID 与测试数据，不要求手工填写测试信息；Gate 不自动启动、重启或停止 PostgreSQL、Redis、Backend 等服务，只验证本地前置服务状态。

在新的本地结果产生前，不将 B6 标记为通过，也不提前进入 Phase 2.9。

## 7. 相关设计约束

- 不创建第二套 Execution / Frontier / Delegation 状态机。
- 不使用 Mock 替代 Real API + PostgreSQL 验收链路。
- 测试脚本负责编排，不在测试脚本中复制生产业务逻辑。
- 本地 Gate 必须明确区分前置服务未启动、测试失败与测试通过。
- 服务启动由开发者按照项目本地运行说明完成，B6 Gate 本身禁止自动启动、重启或停止任何服务。
