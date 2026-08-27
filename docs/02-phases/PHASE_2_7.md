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
- Multi-frontier Join Recovery：Recovery Bootstrap 在进入 Join frontier 前，从 Planner selected predecessors 的 durable Node outputs 重新计算 merged state，并与最新 `frontier_completed` Checkpoint state 做严格一致性校验；drift 或缺失 predecessor 时立即拒绝 Recovery；
- Replay Decision Convergence：Decision Trace 写入前强制复用既有 Replay Guard，对相同 durable completed facts 的历史 Decision、frontier 与 selected predecessor 做收敛校验；不同 fingerprint 或 payload drift 在任何 flush/commit 前立即拒绝；
- **Recovery / Replay lifecycle closure：Resume Contract 的幂等命中现在必须同时证明对应 Resume Execution 已建立 Durable Frontier；缺失 Frontier 的不完整 Resume 不得被伪装成成功 `idempotency_hit`。**
- **Durable Resume Checkpoint continuation：线性 Resume 已在 Runtime 主入口过滤 completed Node，并在全部 Node 已完成时直接 terminalize Execution。**
- **Durable Frontier Multi-frontier checkpoint boundary：Branch Node facts 与 Frontier completion Checkpoint 现在只保留一个正式持久化入口，避免共享 Runtime helper 与 Durable Frontier progression 重复追加 `frontier_completed`。**
- **Durable Frontier Completion Contract Hardening：统一 progression primitive 现在在任何持久化动作前拒绝 `frontier_completed` 携带 Node identity/status/input/output，正式阻断 Node-level 与 Execution-level durable fact 混写。**
- **Durable Frontier Terminal Execution Recovery Guard：过期 Frontier 回收现在只允许关联 Execution 仍为 `pending/running` 时进入 `retry_wait`，completed/failed/cancelled Execution 的旧 Frontier 不再被 Recovery 重新激活。**
- **Durable Checkpoint Execution Lifecycle Guard：Checkpoint durable write 在锁定 Execution 后再次校验当前 Execution status 与快照声明一致，stale Worker 不得在 terminalization 后追加旧的 `running/pending` durable fact。**
- **Durable Frontier Identity Canonicalization：Frontier identity key 对并行 Node 集合进行规范化排序，同一 Execution / Version / Decision 下仅因 Planner 遍历顺序不同不会生成第二个逻辑 Frontier。**

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
Durable Frontier progression
      ↓
frontier_completed
      ↓
Join frontier
```

没有 Branch Checkpoint 或任一 Branch 写入失败时，不得声明 Join ready，也不得生成 merged state。Durable Frontier Worker 不得在共享 Runtime helper 与 progression primitive 中重复追加同一 completion Checkpoint。

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

`record_dag_decision()` 已将 Replay Guard 提升为 Decision 写入前强制边界，不能通过更换 fingerprint 绕过 Guard 并追加第二条 Decision Trace。

### 3.5 Resume Lifecycle Closure

Resume 的确定性幂等键只能证明恢复请求 identity，不足以证明 Resume 已完成 Bootstrap。幂等命中必须继续证明：

```text
Source Checkpoint
      ↓
Deterministic Resume Identity
      ↓
Resume Execution lineage
      ↓
Completed Node lineage + Durable Frontier
      ↓
idempotency_hit / Worker scheduling
```

`WorkflowExecutionResumeContractService` 在返回 `idempotency_hit` 前检查同一 tenant 下的 Resume Durable Frontier。若 Frontier 缺失，立即拒绝并暴露不完整 Recovery lifecycle；不会创建第二个 Resume，也不会吞掉恢复请求。

### 3.6 Tenant / Lineage Closure

Recovery 查询均使用当前 locked Execution 的 `tenant_id`；Resume 必须固定 Source Workflow Version，并保存且重新校验真实 Source Checkpoint sequence；Node lineage、Checkpoint、Resume、Recovery Trace 不得形成跨 tenant / cross-execution replay。

### 3.7 Frontier Completion Atomicity

Durable Frontier 成功路径必须满足单一事务边界：

```text
NodeExecution completed facts
        ↓
complete_frontier_with_checkpoint()
   ├── current Frontier → completed
   ├── one frontier_completed Checkpoint
   └── deterministic Next Frontier
        ↓
       COMMIT
```

共享 `WorkflowRuntime` 可以继续保留普通 Runtime 所需的 Checkpoint 行为，但 Durable Frontier Adapter 必须使用不提前追加 completion Checkpoint 的 Multi-frontier 执行入口，让最终 completion fact 只由 Frontier progression 产生。

### 3.8 Execution Lifecycle / Checkpoint Closure

Checkpoint 写入不能只证明 Worker ownership/fencing 正确，还必须证明写入快照仍对应锁定后的 Execution 生命周期：

```text
Lock Execution
    ↓
Tenant / Worker fencing
    ↓
Existing idempotent boundary?
    ├── yes → return existing fact
    └── no
         ↓
current execution.status == requested execution_status
    ├── no  → reject 409
    └── yes → allocate sequence → flush
```

该边界与 terminal Frontier Recovery Guard 配合，阻断 stale Worker 在 Execution terminalization 后写入旧 `running/pending` durable fact。

### 3.9 Frontier Identity Canonicalization

并行 Frontier 的 `node_ids` 是逻辑 Node 集合，而不是 identity key 的遍历顺序。`WorkflowFrontierIdentity.key()` 现在在生成幂等键前对 Node ID 做规范化排序：

```text
Planner A: [node-c, node-a, node-b]
Planner B: [node-b, node-c, node-a]
             ↓
        canonical key
             ↓
        same Frontier
```

该规则只作用于 identity key，不改变实际 `node_ids` 的执行顺序；因此不会把 identity canonicalization 误当成 Runtime execution ordering。tenant、Execution、Workflow Version、Decision fingerprint 仍全部参与 identity，避免跨 Execution / Version / Decision 错误合并。

## 4. 本轮单元测试

新增 / 更新：

```text
backend/tests/unit/test_frontier_identity.py
```

覆盖：

- 相同 Execution / Version / Decision 下，仅并行 Node 集合顺序变化时 identity key 必须相同；
- Execution、Workflow Version、Decision fingerprint 任一维度变化时 identity key 必须不同。

**当前环境无法在本地启动仓库执行 pytest，因此不得记录 Unit Test PASS；仅保留待开发者本地实际执行。**

## 5. 当前交付状态

```text
Conditional Branching Closure                 ✅
Durable Frontier Scheduling                   ✅
Recovery / Resume Checkpoint lineage          ✅
Multi-frontier Checkpoint boundary            ✅
Execution fencing generation                  ✅
Stale Worker Checkpoint late-write guard      ✅
Node → Checkpoint fencing propagation         ✅
Checkpoint durable write boundary             ✅
Multi-frontier Join Recovery                  ✅
Replay decision convergence                   ✅
Resume lifecycle idempotency closure         ✅
Durable Resume Checkpoint continuation        ✅
Durable Multi-frontier completion boundary    ✅
Durable Completion Contract Hardening         ✅
Terminal Execution Frontier Recovery Guard    ✅
Checkpoint Execution Lifecycle Guard          ✅
Durable Frontier Identity Canonicalization   ✅ 本轮

        ↓

Next Frontier / terminalization / recovery convergence
  └── 继续开发，不以测试流程阻塞主线
```

Unit Test 实际执行与 Real API acceptance 继续按开发准则暂停，不阻塞主线代码推进。Real API acceptance 后续必须验证真实 HTTP + PostgreSQL + Scheduler/Worker → Runtime。

## 6. 本轮交付说明

本轮继续沿 Durable Frontier → Next Frontier → Execution terminalization → Recovery convergence 主线推进。发现现有 `WorkflowFrontierIdentity.key()` 虽然声称 Node 顺序不应产生第二个 Frontier，但实际直接拼接 `node_ids`，导致同一并行 Node 集合在 Planner / Resume 遍历顺序发生变化时可能产生不同 identity key。本轮将 identity key 规范化为排序后的 Node 集合，并保留原始 `node_ids` 作为 Runtime 执行顺序，避免把 identity 与 execution ordering 混为一谈。

本轮没有创建第二套 Planner、Runtime、Repository 或 Provider；仅收紧既有 Frontier identity contract，并新增对应 Unit Test。完整 pytest / Regression / E2E / Real API 流程继续暂停。
