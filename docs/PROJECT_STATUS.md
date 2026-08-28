# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前阶段：**Phase 2.7 Advanced Workflow Orchestration 主线生产开发已完成；本地 Backend Unit / Default Regression 已通过，进入 Migration、Real API、Frontend / E2E 验收收口，同时启动 Phase 2.8-A Multi-Agent Collaboration Contract 冻结。**
- Phase 2.2 Retrieval Production Quality：已正式关闭。
- Phase 2.3 Model Provider Governance：已正式关闭。
- Phase 2.4 Durable Scheduler：生产实现已完成并收口。
- Phase 2.5 Scheduler → Worker Execution Decoupling：已正式关闭。
- Phase 2.6 Durable Execution Checkpoint Foundation：生产代码实现已完成；DAG 分支 Resume / 多-frontier Runtime 已完成主线收口。
- Phase 2.7 Conditional Branching、Durable Frontier Scheduling、Recovery / Replay Closure：**主线生产开发已完成；本轮本地回归修复已验证通过。**

## Phase 2.7 主线完成清单

- Durable Resume Bootstrap、Recovery Trace 原子事务、Join predecessor contract、tenant / version / checkpoint lineage guard：✅
- Decision Replay Guard、Multi-frontier Checkpoint boundary、Execution fencing、stale Worker late-write guard、Node → Checkpoint fencing propagation：✅
- Multi-frontier Join Recovery、Replay Decision Convergence、Resume lifecycle idempotency、Incomplete Resume Bootstrap reconcile：✅
- Multi-frontier Runtime `frontier_completed` Execution-level Checkpoint：✅
- DAG Next Frontier deterministic identity：✅
- `frontier_completed` checkpoint idempotency：✅
- DAG Frontier → Durable Frontier atomic progression bridge：✅
- Durable Frontier → same-Execution Worker ownership reuse：✅
- Durable Frontier expired-lease recovery：✅
- Durable Frontier Execution-aware Claim：✅
- Durable Frontier Runtime Entry Contract：✅
- Durable Frontier completed-Node Resume：✅
- Durable Frontier Retry Budget Resume：✅
- Durable Frontier Checkpoint Continuation：✅
- Durable Frontier Multi-frontier Completion Boundary：✅
- Durable Frontier Completion Contract Hardening：✅
- Durable Frontier Terminal Execution Recovery Guard：✅
- Durable Checkpoint Execution Lifecycle Guard：✅
- Durable Frontier Identity Canonicalization：✅
- Durable Frontier Terminalization Transaction Boundary：✅
- Durable Frontier Terminalization Ownership Recheck：✅
- Durable Frontier Duplicate Completion Convergence：✅
- Durable Frontier Recovery Execution Lease Guard：✅
- Durable Frontier Claim Head-of-Line Guard：✅
- Durable Frontier Failure Terminalization Transaction Boundary：✅
- Durable Frontier Completion Source Binding：✅
- Durable Frontier Recovery Multi-frontier Re-entry：✅
- Durable Frontier Stale Lease Completion Guard：✅
- Durable Frontier Execution Worker Epoch Binding：✅
- Durable Checkpoint Worker Lease Write Guard：✅
- Durable Frontier / Execution Atomic Lease Heartbeat：✅
- Durable Frontier Base Runtime Lease-Lost Abort：✅
- Durable Frontier Planner Runtime Lease-Lost Abort：✅
- Durable Frontier Failure Convergence Ownership Guard：✅
- Durable Frontier Runtime Consumption Guard：✅
- Durable Frontier Next-frontier Duplicate Consumption Guard：✅
- Durable Frontier Claim-layer Duplicate Consumption Guard：✅
- Durable Frontier Terminalization Lock-order Closure：✅
- Durable Frontier Terminal Replay Binding Closure：✅
- Durable Frontier Terminal Replay Lifecycle Closure：✅
- Durable Frontier Success/Failure Terminalization Sibling Closure：✅
- Durable Frontier Replay Duplicate Fact Closure：✅
- Checkpoint writer Replay ownership independence：✅
- Completion fact mismatch fail-closed：✅
- Legacy Checkpoint `append()` Durable writer boundary：✅
- Replay Execution lock boundary：✅
- Generic Execution `completed/failed` terminalization Frontier bypass：✅

## 当前代码级不变量

```text
Success terminalization              ✅
Failure / retry exhaustion           ✅
Recovery × terminal                  ✅
Replay × terminal                    ✅
Duplicate completion                ✅
Stale Worker / lease-loss            ✅
Checkpoint writer / Replay symmetry  ✅
Execution terminal write bypass      ✅
```

关键 Durable 不变量：

- terminal Execution 不进入 Claim / Recovery 可消费条件；
- Frontier lease 与 Execution ownership 同时失效后才允许 Recovery；
- stale Worker 不得完成或失败 Frontier；
- Checkpoint lifecycle 必须与锁定后的 Execution 一致；
- `frontier_completed` 必须绑定 source Frontier；
- 同一 source Frontier + completion reason 的多个 completion fact 必须 fail-closed；
- Replay identity 不包含 ephemeral `worker_owner`；
- Success / Failure terminalization 统一遵循 Frontier → Execution 锁序；
- Execution 通用 `completed/failed` 入口不得绕过活动 Frontier guard。

## 2026-08-28 本地回归结果

以下结果来自开发者实际本地执行，不是预填结果：

### Phase 2.7 受影响测试 targeted

```text
uv run pytest -q \
  tests/unit/test_workflow_automatic_recovery_service.py \
  tests/unit/test_workflow_checkpoint_frontier_idempotency.py \
  tests/unit/test_workflow_dag_decision_trace_idempotency.py \
  tests/unit/test_workflow_frontier_repository.py \
  tests/unit/test_workflow_recovery_lifecycle_closure.py \
  tests/unit/test_workflow_recovery_scheduler.py \
  tests/unit/test_workflow_resume_api_contract.py

27 passed in 1.23s
```

### Durable Resume / Execution / DAG / Frontier targeted regression

```text
scripts/test/workflow/01_resume_runtime_regression.ps1

96 passed in 2.06s
```

### Backend full unit regression + RuntimeWarning gate

```text
scripts/test/workflow/02_full_unit_regression.ps1

811 passed, 3 skipped, 41 deselected in 36.54s
[PASS] Backend full unit regression completed successfully without RuntimeWarning.
```

### Backend default regression

```text
uv run pytest -q

811 passed, 3 skipped, 41 deselected in 33.55s
```

因此，前一轮 7 个失败已经全部收口；没有残留 RuntimeWarning。3 个 skipped 与 41 个 deselected 属于当前测试选择规则，不计为失败。

## 已修复的上一轮真实问题

- Recovery automatic service 的 async double 与实际 coroutine contract 对齐；
- Frontier completion mismatch fixture 改为验证 fail-closed，而不是伪造幂等成功；
- DAG decision trace fixture 改用连续 `execute()` 返回序列；
- Frontier claim fixture 补齐 overlap query 与 `attempt=0` 初始状态；
- Incomplete Resume reconcile fixture 对齐事务边界；
- Recovery Scheduler fixture 对齐真实 session 生命周期与结构化日志；
- Resume API route double 补齐 `refresh()`。

以上问题均通过后续本地回归验证，不降低生产代码的 tenant、lease、fencing、replay 或 lifecycle 安全约束。

## 当前验收顺序

```text
Backend Unit / Default Regression       ✅
        ↓
Migration / DB verification              ← 下一步
        ↓
Real HTTP API Gate                       ← 紧随其后
        ↓
Frontend Gate
        ↓
Browser / Frontend-Backend E2E（如范围需要）
        ↓
本地手动场景
        ↓
Phase 2.7 Acceptance / Status / Error 收口
        ↓
Phase 2.8-A Multi-Agent Contract 冻结
        ↓
Phase 2.8 Backend Domain + API 实现
```

## Phase 2.8-A 下一任务

已新增 `docs/02-phases/PHASE_2_8_A_CONTRACT.md`，冻结 Multi-Agent Collaboration 首版边界：

- 受治理 Agent Delegation；
- tenant / agent version / permission guard；
- delegation idempotency；
- context isolation；
- depth / active-count / timeout / model budget；
- Worker completion fencing；
- Audit / Trace 父子链路；
- 不引入第二套 Workflow Retry / Recovery 状态机。

**Contract 通过前不创建 Multi-Agent Migration 或生产 Service / Runtime，避免先写代码再返工数据模型和权限边界。**

## 当前未执行 Gate

以下均必须以开发者本地实际执行结果为准，目前不标记 PASS：

- `uv run alembic upgrade head` / migration head verification；
- Real HTTP API Gate；
- Frontend Vitest / production build；
- Browser / Frontend-Backend E2E；
- Phase 2.7 最终人工场景验收。
