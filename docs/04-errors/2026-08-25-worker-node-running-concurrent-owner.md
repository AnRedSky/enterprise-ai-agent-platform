# Worker：失去 Execution ownership 后继续推进 Node 状态

## 1. 现象

本地独立 Worker Service 运行期间出现：

```text
fastapi.exceptions.HTTPException: 409: Node 不允许从 running 到 running
```

异常位置为 `WorkflowRuntime.execute()` 调用 `WorkflowExecutionService.transition_node()` 的节点启动阶段。

## 2. 根因

Phase 2.5 已通过 PostgreSQL `worker_owner / worker_lease_expires_at` 实现 Execution claim lease。多个 Worker 可以合法并行消费任务；当某个 Worker 的 lease 因进程暂停、数据库异常或长时间运行而失效后，另一个 Worker 可以重新 claim 同一个 pending Execution。

旧实现虽然会在 claim 时写入新的 `worker_owner`，但 Runtime 后续的 `transition()` / `transition_node()` 没有再次验证“当前数据库 owner 是否仍然是最初 claim 的 Worker”。因此旧 Worker 可能在新 Worker 已接管后继续推进同一 Execution 的节点状态，最终与新 Worker 的 Node Execution 状态产生竞争，表现为 `running -> running` 非法转换。

这属于 Worker lease 的 **ownership fencing 缺失**，不是 Node 状态机本身应该允许 `running -> running`。

## 3. 修复

本轮直接在正式 `WorkflowExecutionService` 增加 ownership fencing：

1. `_lock_execution()` 每次状态转换都重新读取并锁定 PostgreSQL Execution 行；
2. 对 Worker claim 出来的 Execution，使用对象中保存的 `worker_owner` 与数据库最新 owner 比较；
3. owner 不一致时返回 `409 Workflow Execution Worker ownership 已失效`；
4. `transition()` 与 `transition_node()` 因此都受到同一 ownership fence 保护；
5. Worker 对该 409 不再打印为普通 Workflow 执行失败，而是将自身视为 stale consumer 并主动放弃当前任务；
6. 不修改 `Node running -> running` 状态机规则，不允许通过放宽状态机掩盖并发 ownership 问题。

## 4. 设计边界

本修复只解决 **Worker lease 失效后的并发写保护**。

不引入：

- running Execution 自动 resume；
- Scheduler 重新执行 Runtime；
- MQ / Kafka / Celery；
- 第二套 Runtime / Execution Service；
- API / Scheduler 进程边界修改。

如果 Worker 在 Runtime 已进入 running 后永久崩溃，后续仍需要独立的 durable execution / checkpoint 机制解决恢复问题；本阶段不伪造恢复语义。

## 5. 测试要求

针对代码修复必须至少执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_workflow_execution_worker_fencing.py tests/unit/test_workflow_worker.py
uv run pytest -q
uv run alembic upgrade head
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

Real API Gate 前必须确认没有旧 Worker 进程继续运行旧代码。若存在多个 `run_worker.py`，应先停止旧进程，再使用修复后的 `main` 启动唯一测试 Worker；否则测试结果无法证明本轮代码。

Scheduler / Worker Restart Acceptance 仍按独立服务脚本执行，并要求目标后台服务独占测试环境。
