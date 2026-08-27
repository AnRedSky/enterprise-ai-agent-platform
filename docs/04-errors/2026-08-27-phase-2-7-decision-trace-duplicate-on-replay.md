# Phase 2.7 — Recovery Replay 重复 Decision Trace

- 日期：2026-08-27
- 阶段：Phase 2.7-A Conditional Branching Durable Recovery Closure
- 类型：Durable Recovery / Trace Idempotency
- 状态：已修复

## 1. 问题

Recovery Worker 重试或 Runtime 重复解析 DAG context 时，会再次生成 `workflow.dag.frontier_decided` Trace event。

此前 Runtime 每次进入 `_record_dag_frontier_decision()` 都调用通用 Trace 写入，没有以 Decision fingerprint 建立幂等边界。因此同一个 durable Decision 可能产生多条完全相同的审计事件。

## 2. 风险

重复 Trace 不会直接改变 PostgreSQL NodeExecution / Checkpoint，但会造成：

- Decision lineage 噪声；
- Recovery replay 审计难以区分真正的新 Decision 与重试；
- 后续基于 Trace 做一致性对账时出现重复事实；
- Worker 重试次数与 Trace event 数量错误绑定。

## 3. 修复

新增 `WorkflowRecoveryTraceLinkService.record_dag_decision()`，使用以下组合形成 Decision identity：

```text
execution_id
+ tenant_id
+ workflow_version_id
+ trace_id
+ decision_fingerprint
```

命中已有 Decision event 时直接返回，不创建新事件。

不同 fingerprint 仍必须先通过 `assert_dag_decision_replay_consistent()`；若相同 durable completed facts 产生不同 fingerprint，立即拒绝 Recovery。

## 4. 状态边界

Trace 仍然不是 Recovery source of truth：

```text
WorkflowNodeExecution
WorkflowExecutionCheckpoint
        ↓
Condition Evaluator / DAG Planner
        ↓
Decision fingerprint
        ↓
Trace（审计 + replay consistency）
```

本修复不增加第二套状态存储，也不把业务 `state_data` 写入 Decision Trace。

## 5. Unit Test

新增：

```text
backend/tests/unit/test_workflow_dag_decision_trace_idempotency.py
```

覆盖：

- 无 trace identity 不创建 Decision event；
- 相同 Decision identity 命中已有 event 时幂等返回；
- 新 event 只保存审计 metadata，不包含业务 state_data；
- 新 event 正常 flush / commit。

当前环境未执行仓库本地 pytest，因此不记录测试 PASS。
