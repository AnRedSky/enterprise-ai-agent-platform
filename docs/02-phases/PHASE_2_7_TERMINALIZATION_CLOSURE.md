# Phase 2.7 — Terminalization / Replay Closure

> 状态：**主线开发完成，测试待执行**。
> 基线：`main`，2026-08-27。
> 所属阶段：Phase 2.7 Advanced Workflow Orchestration / Durable Recovery Closure。
> 主阶段文档：`docs/02-phases/PHASE_2_7.md`。

## 1. 主线目标

在 Durable Frontier Claim、Runtime Consumption、Checkpoint fencing、Recovery、Success / Failure convergence 已建立的基础上，完成终态一致性与 Replay convergence 收口。

本阶段不新增第二套 Workflow Runtime 或 Planner；最终目标是保证同一 Durable fact 在重复 completion、retry、recovery、stale Worker、terminalization 与 replay 场景下只能收敛到一个合法结果。

## 2. 主线完成项

### 2.1 Claim / Progression 并发 fencing
- 同一 Execution 的活动 Frontier Node-set overlap 在 Claim 前拒绝；
- disjoint parallel Frontier 仍允许并行；
- Next Frontier 创建前检查同 Execution 活动 Frontier Node-set；
- Claim / progression 与 terminalization 统一保持 `Frontier → Execution` 锁顺序；
- overlap 在 durable transaction 内拒绝，不依赖 Runtime 内存状态兜底。

### 2.2 Worker / Runtime fencing
- Execution worker epoch、Frontier attempt 与 Worker lease 分层校验；
- stale Worker 不得完成、失败或写入新的 durable fact；
- heartbeat 在同一短事务内续租 Frontier 与 Execution；
- lease loss 后取消 Planner / Node Runtime，并回滚，不进入普通 failure convergence；
- Runtime Node execution 前重新证明 Frontier / Execution consumption ownership。

### 2.3 Checkpoint Durable boundary
- Checkpoint 写入锁定 Execution 后再次校验 lifecycle；
- Worker owner / epoch / lease 进入实时 Durable write fencing；
- `(execution_id, sequence)` 已由数据库唯一约束保护；
- legacy `append()` 已纳入统一 Execution Durable boundary；
- `frontier_completed` 禁止从 legacy `append()` 写入，必须绑定 source Frontier 并进入 `append_next_in_transaction()`；
- 同一 source Frontier + completion reason 的多个 completion fact fail-closed；
- lifecycle / payload drift fail-closed，不重新分配 sequence。

### 2.4 Success / Failure terminalization
- Success terminalization 统一经过 Frontier → Execution durable boundary；
- Failure / retry exhaustion 与 Execution failed 共享补偿事务；
- terminalization 前重新验证 owner / fencing / lease / lifecycle；
- Success / Failure sibling Frontier closure 已完成；
- 通用 `WorkflowExecutionService.transition()` 的 `completed/failed` 入口已增加活动 Frontier guard，不能绕过 Frontier terminalization；
- terminal Execution 不再进入 Claim / Recovery 可消费路径。

### 2.5 Replay convergence
- Replay 不使用 ephemeral `worker_owner` 作为 Durable identity；
- Replay 找到唯一 completion fact 后重新锁定关联 Execution；
- Checkpoint lifecycle 必须与当前 Execution lifecycle 一致；
- source Frontier、Workflow Version、decision fingerprint、Node-set、Checkpoint payload、Next Frontier identity 全部严格绑定；
- running completion 必须提供原始 Next Frontier identity；terminal completion 禁止追加 Next Frontier identity；
- 同一 source Frontier 存在多个 completion fact 时 fail-closed；
- Replay 不通过“最新 sequence”猜测权威事实；
- 新 Worker 可以收敛已提交 completion fact，不依赖历史 Worker ownership。

## 3. 最终 Durable 不变量审计结论

### Success / Failure terminalization

已代码级确认：

- `completed / failed / cancelled` Execution 不会进入 `claim_next_frontier()` 的可消费条件；
- `recover_expired_frontiers()` 仅处理 `pending / running` Execution，因此 terminal Execution 不会通过旧 Frontier Recovery re-entry；
- retry exhaustion 已在 Frontier failure convergence 中收口到 Execution failed；
- Success terminalization 对 sibling Frontier 做活动状态检查；
- Failure terminalization 关闭活动 sibling Frontier；
- terminalization 与 Frontier progression 使用统一 `Frontier → Execution` 锁序；
- stale Worker 的 owner / attempt / lease 校验位于最终 durable transition 边界。

### Replay convergence

已代码级确认：

```text
same source Frontier
      ↓
same completion fact
      ↓
same Execution / Version
      ↓
same decision fingerprint
      ↓
same Node-set
      ↓
same Checkpoint payload / lifecycle
      ↓
same Next Frontier identity
      ↓
same Durable result
```

任一 identity / payload / lifecycle drift 均 fail-closed。

### Checkpoint writer / Replay symmetry

已确认原始 completion 与 Replay 均以 `frontier_id + checkpoint_reason + execution lifecycle + payload + next Frontier identity` 作为 Durable convergence 边界；历史 `worker_owner` 只用于实时 fencing，不参与 Replay identity。

### Durable write boundary

已完成 `CheckpointService.append()` 旁路收口，并通过全仓领域路径审计确认 `frontier_completed` 的正式写入入口为 `append_next_in_transaction()`。数据库 sequence uniqueness 已存在，不重复创建 migration。

## 4. Unit Test 实现

主线相关 Unit Test 已补充/调整，包括：

```text
backend/tests/unit/test_frontier_duplicate_consumption.py
backend/tests/unit/test_frontier_terminal_replay_lifecycle.py
backend/tests/unit/test_frontier_terminalization_sibling_guard.py
backend/tests/unit/test_frontier_failure_terminalization.py
backend/tests/unit/test_frontier_lock_order.py
backend/tests/unit/test_frontier_replay_lifecycle_audit.py
backend/tests/unit/test_checkpoint_replay_worker_independence.py
backend/tests/unit/test_checkpoint_duplicate_completion_guard.py
backend/tests/unit/test_execution_terminalization_boundary.py
```

Unit Test 只作为生产主线断言实现；本阶段尚未执行完整测试 Gate。

## 5. 测试状态

按照 `docs/01-governance/DEVELOPMENT.md`，当前只完成生产代码与 Unit Test 实现，**未执行**：

- `pytest`；
- Backend Full Regression；
- Alembic migration verification；
- Frontend Gate；
- Real API；
- Browser E2E；
- 本地手动测试。

任何未执行项目不得记录为 PASS。

## 6. Phase 2.7 结论

**Phase 2.7 主线生产开发已完成。**

下一阶段不再新增主线 Durable fencing；按照项目既定顺序切换到本地测试与验收：先准备环境，再执行 Unit / Backend Regression / Migration / Real API / Frontend / E2E，并根据真实执行结果修复发现的问题。
