# Phase 2.7 — Advanced Workflow Orchestration / Conditional Branching

> 状态：**开发中**。
> 基线：`main`，2026-08-27。
> 当前交付单元：Phase 2.7-A Conditional Branching Durable Recovery Closure。
> Contract：`docs/02-phases/PHASE_2_7_A_CONTRACT.md`。

## 1. 当前目标

在现有 Workflow DAG、Checkpoint、Resume、Branch、Join 基础上增加确定性 Conditional Branching，并保证首次执行与 Durable Resume 使用同一套 Planner / Runtime 语义；恢复过程只能依赖持久化完成事实，且所有完成 Node state 与 Checkpoint 读取均保持 tenant boundary。

```text
持久化 Node state
      ↓
Condition Evaluator
      ↓
Conditional DAG Planner
      ↓
selected frontier
      ↓
existing Branch / Join / Runtime
      ↓
Checkpoint / Trace
      ↓
Recovery Resume
      ↓
重新构建 frontier
```

不引入第二套 DAG Planner、Runtime 或 State Merge；条件规则只存在于统一 Condition Evaluator，Runtime 只消费 Planner 结果。

## 2. 已完成实现

- `WorkflowConditionEvaluator`：有限 JSON Condition DSL；
- `eq / ne / gt / gte / lt / lte / in / contains`；
- `and / or / not` 短路求值；
- 点号路径读取当前 `state_data`；
- 严格 JSON 类型比较；
- Condition 最大深度 8、最大节点数 64；
- DAG Edge 支持 `condition` / `default`；
- 同一 source 禁止无条件边与条件/default 边混用；
- 同一 source 最多一个 default；
- Conditional frontier 按 Definition 顺序确定性选择；
- 多个条件同时命中允许形成并行 frontier；
- Planner 输出 selected predecessor facts；
- Join readiness 消费 Planner 已选 predecessor；
- 首次执行与 Resume 均通过统一 DAG Planner；
- 多 root 首次执行为每个 root 建立独立输入 state；
- `dag_runtime.py` 不复制基础 Runtime 的 DAG state / Resume 逻辑；
- Conditional Join 只消费 Planner selected predecessor；
- Durable Resume completed Node 查询强制当前 `tenant_id` scope；
- Checkpoint latest 查询通过 `WorkflowExecution` JOIN 支持 tenant scope；Automatic Recovery 强制使用当前 Execution 的 `tenant_id`；
- Resume Contract 在 Source Execution row lock 后再次强制使用 `locked_execution.tenant_id` 查询最新 Checkpoint；
- Runtime 持久化 `workflow.dag.frontier_decided` decision metadata；
- Planner 生成 deterministic `decision_fingerprint`，并绑定 completed Node facts、条件 source state、frontier 与 selected predecessor；
- Runtime Plan 显式携带 Planner fingerprint，Runtime 不复制 Decision identity 计算逻辑；
- Decision Trace 不保存业务 `state_data`，不能替代 PostgreSQL durable facts；
- Multi-frontier Executor 只有在所有 Branch Checkpoint callback 成功后才允许生成 merged state 并声明 `join_ready=true`；
- 未提供 Checkpoint writer 时仍可收集 Branch execution result，但保持 `join_ready=false` 且不生成 merged state；
- 同一 Recovery trace 下相同 durable completed facts 必须保持相同 `decision_fingerprint`，Replay Guard 对不一致 Decision 立即失败；
- DAG Decision Trace 在同一 execution + tenant + workflow version + trace + decision fingerprint 下幂等落库，Recovery 重试不会重复创建相同 Decision event；
- 顺序 Resume Sequence Planner 完整传递 Planner 的 selected predecessor 与 decision fingerprint，不允许在顺序 Runtime 边界丢失 Durable Decision identity；
- Checkpoint 自动序号分配先锁定目标 `WorkflowExecution` 再读取最大 sequence，确保同一 Execution 的并发 Checkpoint 写入具有确定的序号分配边界；
- Checkpoint 若绑定 Node，则 Recovery 可通过 `assert_node_fact_complete()` 校验 NodeExecution 的 node、status、attempt、output_data；execution-level checkpoint 不要求 NodeExecution；
- Recovery Trace → Resume lineage 强制校验 Source/Resume relationship、tenant、workflow version 与真实存在的 `resume_checkpoint_sequence`，并将 checkpoint sequence 作为 lineage audit metadata。

## 3. Durable Recovery Closure 推进

### 3.1 Conditional Decision 持久化 Trace Fact

Planner 得到：

```text
completed_node_ids
frontier_node_ids
selected_predecessor_node_ids
condition source state
```

Runtime 将这些可重建 metadata 持久化为 `workflow.dag.frontier_decided` Trace fact，并使用 Planner 生成的 deterministic `decision_fingerprint` 支持审计与 replay 对账。

**不持久化业务 `state_data`。** Trace 不是 Recovery source of truth。

### 3.2 Recovery Source of Truth

```text
PostgreSQL
   │
   ├── WorkflowExecution
   ├── WorkflowNodeExecution.completed
   └── WorkflowExecutionCheckpoint
             │
             ▼
       DAG Resume Planner
             │
             ▼
      Conditional Evaluator
             │
             ▼
       selected frontier
```

`workflow.dag.frontier_decided` 只能用于审计与 replay consistency guard，Worker 重启后仍必须从 durable Node / Checkpoint facts 重新计算 frontier。

### 3.3 Tenant Boundary

当前 Recovery 正式路径统一遵循：

```text
Source Execution
      ↓ lock
locked_execution.tenant_id
      ↓
Checkpoint.latest(..., tenant_id=...)
      ↓
Resume assessment
      ↓
Resume idempotency lookup
```

Node completed facts、Checkpoint、Resume Contract 的读取均不得退回无 tenant scope 的正式 Recovery 查询。

### 3.4 首次执行 Multi-root

首次执行且没有 completed Node 时，每个 root 使用独立 input state snapshot，避免后续 branch state 互相污染。

### 3.5 Branch Checkpoint Gate

Multi-frontier Branch execution 现在严格区分：

```text
Branch executed
      ↓
Branch Checkpoint callback
      ↓ success for every frontier Branch
merged state
      ↓
join_ready = true
```

若没有 Checkpoint writer，或者任一 Branch Checkpoint callback 抛出异常：

```text
不生成 merged state
不声明 Join ready
异常交由上层 Worker / ExecutionService 处理
```

因此 Join readiness 不再可能仅凭内存中的 Branch output 推断。

### 3.6 Recovery Frontier Replay Guard

同一 Recovery trace 下，如果 Planner 再次面对相同的 durable `completed_node_ids`，必须得到相同的 `decision_fingerprint`：

```text
Worker #1
  ↓
Durable completed facts
  ↓
Planner
  ↓
Fingerprint = F1
  ↓
Trace
  ↓
Worker crash
  ↓
Worker #2
  ↓
同一 durable completed facts
  ↓
Planner
  ↓
Fingerprint = F1       → 允许继续
```

若相同 durable completed facts 得到不同 fingerprint：

```text
Recovery Decision Inconsistency
        ↓
立即拒绝继续该 Recovery Decision
```

Replay Guard 只读取 Trace metadata 做一致性对账，不把 Trace 当作业务状态来源；实际条件计算仍以 PostgreSQL Node / Checkpoint facts 为准。

### 3.7 Decision Trace Idempotency

Recovery Runtime 重试时，同一 Decision 不应因为重复调用 `_resolve_dag_context()` 而不断生成重复 Trace event。

当前正式写入边界为：

```text
execution_id
+ tenant_id
+ workflow_version_id
+ trace_id
+ decision_fingerprint
        ↓
唯一 Decision identity
```

命中已有事件时直接复用，不创建第二条相同 Decision Trace；不同 fingerprint 仍先经过 Replay Guard，一旦与同一 durable completed facts 冲突则拒绝 Recovery。

该能力只解决 Trace event 的幂等性，不改变 PostgreSQL NodeExecution / Checkpoint 作为 Recovery source of truth 的原则。

### 3.8 Recovery Trace → Resume Checkpoint Lineage

Recovery 创建 Resume Execution 时，Trace lineage 现在必须证明它对应 Source Execution 的真实 durable checkpoint：

```text
Source Execution
      ↓
Resume.resume_of_execution_id == Source.id
      ↓
tenant / workflow version 相同
      ↓
resume_checkpoint_sequence
      ↓
Source Checkpoint(sequence) 存在
      ↓
recovery.trace_linked
```

`recovery.trace_linked` 事件仅保存身份和 checkpoint sequence metadata，不复制 checkpoint `state_data`。这样独立 Worker 后续恢复 trace identity 时，可以同时审计 Resume 所依据的 durable checkpoint 边界。

## 4. 单元测试

已有：

```text
backend/tests/unit/test_workflow_condition_evaluator.py
backend/tests/unit/test_workflow_conditional_branching.py
backend/tests/unit/test_workflow_runtime.py
backend/tests/unit/test_workflow_dag_runtime_initialization.py
backend/tests/unit/test_workflow_checkpoint_tenant_scope.py
backend/tests/unit/test_workflow_dag_decision_trace.py
backend/tests/unit/test_workflow_resume_contract_tenant_scope.py
backend/tests/unit/test_workflow_dag_executor_checkpoint_gate.py
backend/tests/unit/test_workflow_dag_replay_guard.py
backend/tests/unit/test_workflow_dag_decision_trace_idempotency.py
backend/tests/unit/test_workflow_checkpoint_sequence_allocation.py
backend/tests/unit/test_workflow_checkpoint_fact_completeness.py
```

本轮新增：

```text
backend/tests/unit/test_workflow_recovery_trace_lineage.py
```

覆盖：

- Resume 必须指向 Source Execution；
- Source / Resume 必须保持同一 tenant 与 workflow version；
- `resume_checkpoint_sequence` 必须存在；
- 合法 checkpoint lineage 可以建立。

**当前环境未执行仓库本地 pytest，因此不得记录 Unit Test 为 PASS。**

## 5. 当前下一交付

```text
Condition Evaluator               ✅
DAG Contract                     ✅
Conditional frontier planner     ✅
Initial Runtime                  ✅
Resume Runtime                   ✅
Conditional Join                 ✅
Tenant / Checkpoint boundary     ✅
Decision Trace                   ✅
Decision Fingerprint             ✅
Runtime Plan fingerprint         ✅
Branch Checkpoint Gate            ✅
Recovery Replay Guard             ✅
Decision Trace Idempotency        ✅
Sequence Plan metadata            ✅
Checkpoint sequence serialization ✅
Checkpoint fact completeness      ✅
Recovery Trace Checkpoint Lineage ✅
Unit Test 实际执行                ⏳
Real API acceptance               ⏸ 暂停

        ↓

Phase 2.7-A Durable Recovery Closure
  ├── Conditional decision 可重建性
  └── Trace lineage 连续性
        ↓
Phase 2.7-A Closure
        ↓
Phase 2.7 后续 orchestration capability
```

Phase 2.7 禁止创建第二套 DAG Planner / Runtime / State Merge；Real API acceptance 后续必须验证真实 HTTP + PostgreSQL + Worker → Runtime。
