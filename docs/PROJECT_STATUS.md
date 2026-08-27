# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前远端 `main` 基线：`c7d7a3ccf822d6a1f745fae7f6dcc49f232fd7af`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**API / Scheduler 进程解耦已完成；Frontend / Browser E2E 与历史 Real API 验收已完成，本轮不再作为主线阻塞条件。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**已正式关闭。**
- Phase 2.6 Durable Execution Checkpoint Foundation：**生产代码实现已完成，DAG Resume / Branch / Join / Automatic Recovery / Recovery Trace / Worker Reclaim / Lease Fencing / Lease Loss Active Abort / Terminal Ownership Boundary 均已落地；当前仅等待开发者本地 Unit Test 实际结果完成 Closure。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**
- Phase 2.7 Advanced Workflow Orchestration：**开发中；Conditional Branching 首个交付单元已完成首版生产代码与 Unit Test 覆盖实现，当前等待开发者本地 Unit Test 实际执行。**

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

## Phase 2.7-A 当前实现

- `WorkflowConditionEvaluator` 已建立唯一条件求值入口；
- Condition DSL 支持 `eq / ne / gt / gte / lt / lte / in / contains / and / or / not`；
- 条件只读取当前持久化 Node state，禁止代码执行、外部调用和危险类型转换；
- Condition 深度 / 节点数上限已实现；
- DAG Edge 已扩展 `condition` / `default`；
- 条件边与 default 边的 source 模式、default 数量、重复 edge、未知 Node、循环图继续由统一 DAG Contract 校验；
- Conditional frontier 按 Definition 顺序确定性选择，并允许多个条件同时命中形成并行 frontier；
- Planner 输出 selected predecessor facts；
- Join readiness 只消费 Planner 已选 predecessor，不复制条件解析；
- Resume 从持久化 completed Node output 重新计算 frontier；
- Runtime 复用现有 DAG Runtime Planner / State Merge，不建立第二套 Runtime；
- `backend/tests/unit/test_workflow_condition_evaluator.py` 已补充 Condition Evaluator 的操作符、严格类型、短路求值、结构安全、深度/节点上限等 Unit Test 覆盖；
- `backend/tests/unit/test_workflow_conditional_branching.py` 已覆盖 Conditional frontier、default、并行命中、Join predecessor 与 Runtime Planner Contract。

## 当前开发策略

按当前要求暂停完整测试流程。当前主线只以 **Unit Test 实际执行结果**作为开发验证范围；Backend Full Regression、Frontend Gate、Browser E2E、完整 Release Gate、Real API Acceptance 暂不作为当前主线阻塞条件。测试结果只能记录实际执行结果，不得预填“通过”。

## 最新本地执行限制

当前运行环境无法解析 `github.com`，无法直接 clone / 执行仓库最新 `main` 的本地 pytest；因此本轮没有伪造 Unit Test 结果。远端 `main` 通过 GitHub Repository API 核对，并已直接基于 `main` 完成 Unit Test 覆盖补充与 Phase 文档同步。

## 下一主线

**Phase 2.7-A — Conditional Branching Closure**。

实施顺序：

```text
Contract
  ↓ 已完成
Condition evaluator unit tests
  ↓ 已实现，待本地实际执行
DAG Contract extension
  ↓ 已完成
Conditional frontier planner
  ↓ 已完成
Runtime integration
  ↓ 首版已完成
Unit Test 实际执行
  ↓ 当前下一步
Real API acceptance
  ↓ 后续
Phase / Acceptance / Status / Error update
  ↓
main
```

Phase 2.7 不得重新创建第二套 DAG Planner / Runtime / State Merge。Real API acceptance 必须验证真实 HTTP + 真实 PostgreSQL + Worker → Runtime；GitHub Actions 不作为开发测试或验收依据。

## 服务版本边界

Checkpoint、Resume、Recovery Policy、Recovery Domain、Scheduler、Worker、HTTP Resume API、Conditional Runtime 的代码更新都需要开发者人工重启受影响进程后才能进行真实联调；测试脚本不得负责启动、停止或重启服务。
