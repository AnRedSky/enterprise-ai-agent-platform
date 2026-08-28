# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前阶段：**Phase 2.7 Advanced Workflow Orchestration 主线生产开发已完成，进入本地测试、回归修复与验收准备阶段。**
- Phase 2.2 Retrieval Production Quality：已正式关闭。
- Phase 2.3 Model Provider Governance：已正式关闭。
- Phase 2.4 Durable Scheduler：生产实现继续收口；Persistence、Runtime、Scheduler API Contract、tenant isolation / misfire、API/Scheduler 进程解耦及双循环生命周期监督均已实现。
- Phase 2.5 Scheduler → Worker Execution Decoupling：已正式关闭。
- Phase 2.6 Durable Execution Checkpoint Foundation：生产代码实现已完成；DAG 分支 Resume / 多-frontier Runtime 已完成本阶段主线收口。
- Phase 2.7 Conditional Branching、Durable Frontier Scheduling、Recovery / Replay Closure：**主线生产开发已完成；已开始基于真实本地结果进行回归修复。**

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

## Phase 2.7 最终代码级审计

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

## 当前本地回归结果

开发者于 2026-08-28 在 `backend` 将此前大回归拆分后实际执行：

```text
uv run pytest -q \
  tests/unit/test_durable_resume_runtime.py \
  tests/unit/test_workflow_execution_idempotency.py \
  tests/unit/test_workflow_execution_governance.py \
  tests/unit/test_workflow_dag_runtime_initialization.py

3 failed, 17 passed
```

本轮 3 个失败均已定位为测试 double / fixture 与当前正式 Contract 不一致，而不是因此放宽生产约束：

- DAG Resume Planner 场景使用 `MagicMock.execute`，但断言调用了不存在的 `assert_not_awaited()`；已改为显式 `AsyncMock`。
- Durable Resume Retry budget fixture 缺少当前查询链路需要的 `node_id`；已补齐 durable Node fact 字段。
- DAG 首次执行 fixture 缺少当前 tenant boundary 所需的 `tenant_id`；已补齐租户字段。

已提交对应测试修复，并新增可重复执行的 targeted regression 入口：
`backend/scripts/test/workflow/01_resume_runtime_regression.ps1`。

**注意：以上修复提交后的 PASS 状态尚未由本地重新执行确认，必须以开发者下一次实际运行结果为准。**

## 下一步

```text
本轮 3 个 targeted fixture / mock 修复
  ↓
重新执行 Durable Resume / Execution / DAG targeted regression
  ↓
继续处理下一组 Durable Frontier / Checkpoint / Recovery 回归
  ↓
Backend Unit / Default Regression
  ↓
Alembic head / migration verification
  ↓
Real HTTP API Gate
  ↓
Frontend Gate
  ↓
Browser / Frontend-Backend E2E（如范围需要）
  ↓
本地手动场景
  ↓
根据真实失败结果形成修复提交
  ↓
更新 Acceptance / PROJECT_STATUS
```

测试结果只能来自实际本地执行；未执行不得标记 PASS。
