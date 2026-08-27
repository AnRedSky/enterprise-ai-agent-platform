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
- Decision Trace 不保存业务 `state_data`，不能替代 PostgreSQL durable facts；
- Multi-frontier Executor 只有在所有 Branch Checkpoint callback 成功后才允许生成 merged state 并声明 `join_ready=true`；
- 未提供 Checkpoint writer 时仍可收集 Branch execution result，但保持 `join_ready=false` 且不生成 merged state；
- 无 DAG edges 的历史顺序 Workflow 保留原执行兼容语义。

## 3. 本轮 Durable Recovery Closure 推进

### 3.1 Conditional Decision 持久化 Trace Fact

Planner 得到：

```text
completed_node_ids
frontier_node_ids
selected_predecessor_node_ids
```

Runtime 将这些可重建 metadata 持久化为 `workflow.dag.frontier_decided` Trace fact，并使用 deterministic `decision_id` 支持审计与消费端去重。

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

`workflow.dag.frontier_decided` 只能用于审计，Worker 重启后仍必须从 durable Node / Checkpoint facts 重新计算 frontier。

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
```

本轮新增：

```text
backend/tests/unit/test_workflow_dag_executor_checkpoint_gate.py
```

覆盖单 frontier / Multi-frontier 在缺少 Checkpoint writer 时不得声明 Join ready，以及所有 Branch checkpoint 成功后才能产生 merged state。

**当前环境未执行仓库本地 pytest，因此不得记录 Unit Test 为 PASS。**

## 5. 当前下一交付

```text
Condition Evaluator              ✅
DAG Contract                    ✅
Conditional frontier planner    ✅
Initial Execution Runtime       ✅
Multi-root initialization       ✅
Resume Runtime integration      ✅
Conditional Join                ✅
Runtime inheritance cleanup     ✅
NodeExecution tenant boundary   ✅
Checkpoint tenant boundary      ✅
Conditional Decision Trace      ✅
Resume Contract tenant scope    ✅
Branch Checkpoint Gate          ✅ 本轮完成
        ↓
Durable Recovery Closure
        ├── Checkpoint fact 完整性       ← 继续
        ├── Conditional decision 可重建性 ← 继续
        ├── Trace lineage 连续性         ← 继续
        └── Recovery 后 frontier 一致性   ← 继续
        ↓
Phase 2.7-A Closure
        ↓
Phase 2.7 后续 orchestration capability
```

Real API acceptance 后续必须验证真实 HTTP、真实 PostgreSQL 持久化事实以及 Worker → Runtime 链路；当前不使用 Mock、JSON fixture 或 GitHub Actions 替代本地验收。

## 6. 明确不实现

- 人工审批节点；
- Saga / compensation；
- 通用 Policy DSL；
- 任意代码表达式；
- MQ / Kafka / Event Bus；
- 跨 Workflow Version Resume；
- 第二套 DAG Planner / Runtime / State Merge。
