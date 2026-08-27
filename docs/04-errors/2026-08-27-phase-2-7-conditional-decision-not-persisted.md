# Phase 2.7-A：Conditional Decision 缺少持久化审计事实

## 1. 发现

Conditional DAG Planner 已经能够从持久化 completed Node state 重新计算 frontier 和 selected predecessor，但此前这些 Decision 只存在 Runtime 当前调用栈中。

## 2. 影响

- Recovery 可以重新计算 decision，但无法从 Trace 直接审计当次选择的 frontier；
- Recovery Trace lineage 只有 source/resume Execution 关联，缺少 DAG decision metadata；
- 无法方便地区分“当时选择的 frontier”与“Recovery 后重新计算的 frontier”。

## 3. 修复

在 `backend/app/runtime/workflow/dag_runtime.py` 增加统一 `workflow.dag.frontier_decided` Trace fact，持久化：

- deterministic `decision_id`；
- workflow version；
- completed Node IDs；
- frontier Node IDs；
- selected predecessor Node IDs。

不持久化业务 `state_data`，避免 Trace 变成业务状态存储。

## 4. Source of Truth

Decision Trace 仅用于审计，不作为 Recovery source of truth。Worker 重启后仍必须读取 PostgreSQL `WorkflowNodeExecution.completed` / Checkpoint facts，并重新执行同一个 DAG Planner / Condition Evaluator。

## 5. 验证

新增 `backend/tests/unit/test_workflow_dag_decision_trace.py`，覆盖 Initial multi-root 和 Conditional Recovery decision metadata，并验证业务 state 不进入 Trace。

当前环境未执行 pytest，因此测试状态保持“待开发者本地执行”，不得记录 PASS。
