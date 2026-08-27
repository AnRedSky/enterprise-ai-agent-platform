# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**API / Scheduler 进程解耦已完成；独立 Scheduler recovery acceptance 已通过。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**已正式关闭。**
- Phase 2.6 Durable Execution Checkpoint Foundation：**代码实现完成，当前等待本地 Unit Test 实际结果完成 Closure。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## Phase 2.6 当前实现

- Checkpoint immutable snapshot + transaction boundary；
- Resume Candidate / deterministic idempotency / lineage；
- HTTP Resume API 与 Worker → Runtime Resume；
- Recovery Policy / Automatic Recovery / Recovery Scan；
- Recovery Outcome `created / idempotency_hit`；
- Scheduler parent trace → Recovery child trace → durable Recovery Trace Link；
- DAG Branch State Merge Contract；
- Multi-frontier Runtime Plan / Branch Executor / Join readiness / Join execution；
- Worker expired running Execution reclaim；
- Lease Loss Active Abort：heartbeat 明确失去 ownership 后主动取消 Runtime；
- lease loss telemetry：`outcome=aborted`、`reason_code=WORKER_LEASE_LOST`；
- **Terminal Ownership Boundary：`running → completed/failed/cancelled` 在同一事务中同步清理 `worker_owner`、`worker_lease_expires_at`、`current_node_id` 并写入 `ended_at`，避免 terminal status 与 lease ownership 跨事务短暂不一致。**
- 新增 `backend/tests/unit/test_workflow_execution_terminal_ownership.py`，覆盖 completed / failed / cancelled 三种终态。

## Worker Lease / Fencing Contract

1. `pending` 且无 owner 的 Execution 可以被 Worker claim；
2. `running` 且 lease 已过期的 Execution 可以被新 Worker 在 PostgreSQL 行锁内回收；
3. 回收时先转回 `pending`，再写入新 owner 与新 lease，并递增 `worker_attempt`；
4. 旧 Worker 的状态推进继续通过 `WorkflowExecutionService` ownership fencing；
5. terminal Execution 不允许残留 worker owner / lease，terminal 状态与 ownership 清理必须同事务提交；
6. 旧 Worker 在 heartbeat 明确返回 ownership 丢失后主动停止 Runtime；
7. Worker `finally` 仅保留防御性清理，不承担 terminal ownership 正确性的唯一来源。

## 当前开发策略

按当前要求暂停完整测试流程。当前主线只以 **Unit Test 实际执行结果**作为开发验证范围；Backend Full Regression、Frontend Gate、Browser E2E、完整 Release Gate、Real API Acceptance 暂不作为当前主线阻塞条件。测试结果只能记录实际执行结果，不得预填通过。

## 下一步主线

1. 开发者本地执行 `uv run pytest -q`，补充真实 Unit Test 输出；
2. 若 Unit Test 通过，完成 Phase 2.6 Closure，并同步 Phase / Acceptance / Project Status；
3. Closure 后进入下一正式企业级执行能力，必须先冻结 Product / Backend Contract，再编码；
4. 不重新创建平行 Durable Execution、Lease、Recovery Trace 或 Worker Runtime 抽象。

## 本轮工程错误记录

- `docs/04-errors/2026-08-27-durable-resume-terminal-ownership.md`：记录 terminal status 与 Worker ownership 跨事务短暂不一致问题及修复。

## 服务版本边界

Checkpoint、Resume、Recovery Policy、Recovery Domain、Scheduler、Worker、HTTP Resume API 的代码更新都需要开发者人工重启受影响进程后才能进行真实联调；测试脚本不得负责启动、停止或重启服务。
