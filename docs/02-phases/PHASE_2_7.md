# Phase 2.7 — Advanced Workflow Orchestration / Conditional Branching

> 状态：**开发中**。
> 基线：`main`，2026-08-27。
> 当前交付单元：Phase 2.7-A Durable Recovery Closure。
> Contract：`docs/02-phases/PHASE_2_7_A_CONTRACT.md`。

## 1. 当前目标

在现有 Workflow DAG、Checkpoint、Resume、Branch、Join 基础上形成确定性的 Conditional Branching 与 Durable Recovery 闭环。首次执行、Durable Resume、Multi-frontier、Join Recovery 必须复用同一套 Planner / Runtime / State Merge 语义；Recovery 只能依赖持久化完成事实，并保持 tenant boundary。

```text
Durable Node facts / Checkpoint
            ↓
WorkflowDagResumePlanner
            ↓
selected frontier + selected predecessors + fingerprint
            ↓
Branch / Multi-frontier / Join
            ↓
Node Checkpoint / frontier_completed Checkpoint
            ↓
Recovery Resume Bootstrap
            ↓
Planner rebuild
            ↓
Join merged-state recovery guard
```

禁止创建第二套 DAG Planner、Runtime、Condition Evaluator 或 State Merge。

## 2. 已完成实现

- `WorkflowConditionEvaluator`：有限 JSON Condition DSL，支持 `eq / ne / gt / gte / lt / lte / in / contains / and / or / not`，严格 JSON 类型比较并限制深度/节点数；
- DAG Edge 支持 `condition` / `default`，统一 Contract 校验 source、default、重复 edge、未知 Node 与循环图；
- Conditional frontier 按 Definition 顺序确定性选择，多个条件同时命中可形成并行 frontier；
- `WorkflowDagResumePlanner` 是首次执行与 Resume 的统一 Planner，输出 completed / frontier / selected predecessors / deterministic decision fingerprint；
- Runtime Plan 直接消费 immutable `WorkflowDagResumePlan`，不重复计算 Decision；
- Conditional Join 只消费 Planner selected predecessor，拒绝未知或重复 predecessor；
- Multi-frontier Executor 只有在所有 Branch Checkpoint callback 成功后才生成 merged state 并声明 `join_ready=true`；
- Decision Trace 使用 execution + tenant + workflow version + trace + decision fingerprint 形成幂等 identity，并对 replay payload drift 做一致性校验；
- Durable Frontier 已完成持久化、tenant/key uniqueness、Claim、Worker lease fencing、expired lease recovery、Retry Scheduling、Scheduler → Worker → Runtime bridge；
- `complete_frontier_with_checkpoint()` 已形成 Frontier → Execution/Checkpoint → Next Frontier 原子推进边界；
- Runtime/Planner progression wiring 已接入真实 Durable Frontier Worker；
- Runtime failure 已统一收敛到 Frontier Retry / Failed 生命周期；
- Durable Resume Bootstrap 已在同一事务复制 completed Node lineage、计算首个 Frontier 并幂等入队；
- Resume Source / Resume tenant、workflow version、checkpoint sequence lineage 均有正式边界；
- `frontier_completed` 强制为 Execution-level Checkpoint，禁止携带 Node identity/status；
- Execution `worker_owner + worker_attempt` fencing 已延伸到 Execution / Node / Checkpoint durable write；
- Checkpoint durable write boundary 在真正落库前再次拒绝 Node/Execution-level 混合事实；
- **本轮新增 Multi-frontier Join Recovery**：Recovery Bootstrap 在进入 Join frontier 前，从 Planner selected predecessors 的 durable Node outputs 重新计算 merged state，并与最新 `frontier_completed` Checkpoint state 做严格一致性校验；drift 或缺失 predecessor 时立即拒绝 Recovery。

## 3. Durable Recovery Closure

### 3.1 Recovery Source of Truth

```text
PostgreSQL
   ├── WorkflowExecution
   ├── WorkflowNodeExecution.completed
   └── WorkflowExecutionCheckpoint
             ↓
       WorkflowDagResumePlanner
             ↓
       selected frontier
```

Trace / Decision metadata 只用于审计与 Replay Guard，不能替代 PostgreSQL Durable facts。

### 3.2 Multi-frontier Branch Checkpoint Gate

```text
Branch executed
      ↓
Branch Checkpoint callback
      ↓ all success
merged state
      ↓
frontier_completed
      ↓
Join frontier
```

没有 Branch Checkpoint 或任一 Branch 写入失败时，不得声明 Join ready，也不得生成 merged state。

### 3.3 Multi-frontier Join Recovery

`frontier_completed` 是 Execution-level snapshot，不绑定单个 NodeExecution，因此不能依赖 Node Fact Completeness 校验。Recovery 必须重新建立以下一致性证明：

```text
Source frontier_completed.state_data
             ↕
Planner selected predecessor snapshot
             ↓
completed Node durable outputs
             ↓
WorkflowDagJoinReadinessService
             ↓
唯一 State Merge
             ↓
expected merged state
```

`WorkflowDagJoinRecoveryService` 只负责这一纯内存校验，不读取数据库、不启动 Runtime、不执行条件表达式、不提交事务。`WorkflowExecutionResumeBootstrapService` 仅在最新 Checkpoint 为 `frontier_completed` 且下一 frontier 包含 `join` Node 时启用该 guard。

### 3.4 Replay / Decision Closure

相同 durable completed facts 必须得到相同 `decision_fingerprint`。不同 fingerprint 或历史 Decision payload drift 时立即拒绝 Recovery；条件求值仍只来自统一 Planner / Condition Evaluator。

### 3.5 Tenant / Lineage Closure

Recovery 查询均使用当前 locked Execution 的 `tenant_id`；Resume 必须固定 Source Workflow Version，并保存且重新校验真实 Source Checkpoint sequence；Node lineage、Checkpoint、Resume、Recovery Trace 不得形成跨 tenant / cross-execution replay。

## 4. 本轮单元测试

新增：

```text
backend/tests/unit/test_workflow_dag_join_recovery.py
```

覆盖：

- 从 durable predecessor facts 重建 Join merged state；
- Checkpoint merged state drift 拒绝；
- Recovery 校验不修改输入 state；
- predecessor 未完成时拒绝 Join Recovery。

**当前环境无法在本地启动仓库执行 pytest，因此不得记录 Unit Test PASS；仅保留待开发者本地实际执行。**

## 5. 当前下一交付

```text
Conditional Branching Closure                 ✅
Durable Frontier Scheduling                   ✅ 当前实现范围
Recovery / Resume Checkpoint lineage          ✅
Multi-frontier Checkpoint boundary            ✅
Execution fencing generation                  ✅
Stale Worker Checkpoint late-write guard      ✅
Node → Checkpoint fencing propagation         ✅
Checkpoint durable write boundary              ✅
Multi-frontier Join Recovery                   ✅ 本轮

        ↓

Recovery / Replay Closure
  └── Replay decision convergence
        ↓
最终 Recovery / Replay lifecycle closure
```

Unit Test 实际执行与 Real API acceptance 继续按开发准则暂停，不阻塞主线代码推进。Real API acceptance 后续必须验证真实 HTTP + PostgreSQL + Scheduler/Worker → Runtime。
