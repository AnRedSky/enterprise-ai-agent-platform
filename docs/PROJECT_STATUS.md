# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前阶段：**Phase 2.7 Advanced Workflow Orchestration 主线生产开发已完成，进入本地测试与验收准备阶段。**
- Phase 2.2 Retrieval Production Quality：已正式关闭。
- Phase 2.3 Model Provider Governance：已正式关闭。
- Phase 2.4 Durable Scheduler：生产实现继续收口；Persistence、Runtime、Scheduler API Contract、tenant isolation / misfire、API/Scheduler 进程解耦及双循环生命周期监督均已实现。
- Phase 2.5 Scheduler → Worker Execution Decoupling：已正式关闭。
- Phase 2.6 Durable Execution Checkpoint Foundation：生产代码实现已完成；DAG 分支 Resume / 多-frontier Runtime 已完成本阶段主线收口。
- Phase 2.7 Conditional Branching、Durable Frontier Scheduling、Recovery / Replay Closure：**主线生产开发已完成，测试待执行。**

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

## 当前开发策略

**Phase 2.7 主线生产开发已完成。现在才切换到本地测试与验收。**

当前只实现 Unit Test，尚未执行 pytest、Backend Full Regression、Frontend Release Gate、Browser E2E、Real API Acceptance 或本地手动测试。不得把未执行测试写成通过。

## 最新测试限制

当前环境只能通过 GitHub Repository API 核对和修改远端 `main`，无法在本地启动完整项目执行 pytest / npm。因此本轮没有伪造任何测试结果。

## 下一阶段：本地测试与验收

按照 `docs/01-governance/DEVELOPMENT.md`：

```text
环境检查
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
