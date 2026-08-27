# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前远端 `main` 基线：`936cd9e124ed01b2254a8f30fee67b7ca2b2d0c3`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**API / Scheduler 进程解耦已完成；Frontend / Browser E2E 与历史 Real API 验收已完成，本轮不再作为主线阻塞条件。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**已正式关闭。**
- Phase 2.6 Durable Execution Checkpoint Foundation：**生产代码实现已完成，DAG Resume / Branch / Join / Automatic Recovery / Recovery Trace / Worker Reclaim / Lease Fencing / Lease Loss Active Abort / Terminal Ownership Boundary 均已落地；当前仅等待开发者本地 Unit Test 实际结果完成 Closure。**
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
- Terminal Ownership Boundary：`running → completed/failed/cancelled` 在同一事务中同步清理 `worker_owner`、`worker_lease_expires_at`、`current_node_id` 并写入 `ended_at`；
- `backend/tests/unit/test_workflow_execution_terminal_ownership.py` 覆盖 completed / failed / cancelled 三种终态；
- Issue #49 DAG Resume Contract / Runtime Integration 已完成并关闭；
- Issue #52 Terminal Worker Ownership 修复已完成并关闭。

## 当前开发策略

按当前要求暂停完整测试流程。当前主线只以 **Unit Test 实际执行结果**作为开发验证范围；Backend Full Regression、Frontend Gate、Browser E2E、完整 Release Gate、Real API Acceptance 暂不作为当前主线阻塞条件。测试结果只能记录实际执行结果，不得预填通过。

## 最新本地执行限制

本轮运行环境无法解析 `github.com`，尝试直接 clone 最新 `main` 时因 DNS 无法解析而失败；因此本轮没有伪造本地 pytest 结果。远端 `main` 已通过 GitHub Repository API 核对到上述基线。

## 下一主线

**Phase 2.7 — Advanced Workflow Orchestration / Conditional Branching**。

首个交付单元已经冻结 Contract：`docs/02-phases/PHASE_2_7_A_CONTRACT.md`，并建立 Issue #53。

实施顺序固定为：

```text
Contract
  ↓
Condition evaluator unit tests
  ↓
DAG Contract extension
  ↓
Conditional frontier planner
  ↓
Runtime integration
  ↓
Real API acceptance
  ↓
Phase / Acceptance / Status / Error update
  ↓
main
```

当前只暂停完整 Gate，不暂停主线代码开发；Phase 2.7 不得重新创建第二套 DAG Planner / Runtime / State Merge。

## 服务版本边界

Checkpoint、Resume、Recovery Policy、Recovery Domain、Scheduler、Worker、HTTP Resume API 的代码更新都需要开发者人工重启受影响进程后才能进行真实联调；测试脚本不得负责启动、停止或重启服务。
