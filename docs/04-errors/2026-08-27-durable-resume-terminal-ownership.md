# 2026-08-27 Durable Resume terminal ownership 可观察窗口

## 问题

Durable Resume failure-after-resume 场景中，`WorkflowExecution.status` 进入 `failed` / `completed` / `cancelled` 后，原实现只写入 `ended_at` 与清理 `current_node_id`，`worker_owner` 与 `worker_lease_expires_at` 仍依赖 Worker `finally` 异步释放。

这会产生短暂但真实的可观察不一致：数据库已经显示 Execution 进入 terminal，但旧 Worker owner 仍存在，新 Worker 的 expired-running reclaim / ownership 判断可能在该窗口看到旧 owner。

## 根因

Execution terminal state 与 Worker ownership 不属于同一个事务更新边界。状态转换提交后再由 Worker finally 清理 ownership，导致 terminal status 与 lease 生命周期出现跨事务时序。

## 修复

`WorkflowExecutionService.transition()` 在 `target_status in TERMINAL_EXECUTION_STATES` 时同一事务同步执行：

- `worker_owner = None`；
- `worker_lease_expires_at = None`；
- `ended_at = now`；
- `current_node_id = None`。

这样 terminal status、lease ownership、审计与 Trace 在同一次 commit 中形成原子可观察事实。Worker finally 保留为防御性清理，但不再承担 terminal ownership 正确性的主要职责。

## 回归覆盖

新增 `backend/tests/unit/test_workflow_execution_terminal_ownership.py`，对 `completed`、`failed`、`cancelled` 三种终态验证：

1. owner 被清空；
2. lease 被清空；
3. current node 被清空；
4. `ended_at` 已写入；
5. 状态转换只提交一次事务并完成对象刷新。

## 边界

本修复不修改 Checkpoint、Resume、Scheduler、Recovery Policy、DAG Branch/Join 或 Worker claim 算法，只收口 Execution terminal boundary 与 Worker lease 生命周期的一致性。

## 测试状态

按当前开发策略只保留 Unit Test 作为开发阻塞条件。本环境无法访问项目本地 `backend/.venv`，因此未将测试记录为 PASS；开发者本地执行 `uv run pytest -q` 后再完成 Phase 2.6 Closure。
