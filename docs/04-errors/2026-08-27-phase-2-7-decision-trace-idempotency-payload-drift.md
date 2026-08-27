# Phase 2.7 Error Record — Decision Trace 幂等命中掩盖 Payload Drift

- 日期：2026-08-27
- 阶段：Phase 2.7-A Conditional Branching Durable Recovery Closure
- 类型：Recovery / Trace consistency

## 问题

`record_dag_decision()` 已经使用 execution、tenant、workflow version、trace 与 decision identity 查找已有 `workflow.dag.frontier_decided` event。

原实现命中已有 event 后直接返回，没有重新校验 event 中的 durable Decision payload。

因此如果历史 event 被错误写入或发生数据漂移，新的 Recovery 请求可能因为“幂等命中”而静默接受错误的 frontier / predecessor / completed facts。

## 修复

已有 Decision event 命中后，必须重新验证：

```text
 decision_id
 completed_node_ids
 frontier_node_ids
 selected_predecessors
```

任一字段不一致立即抛出 `ValueError`，不允许通过幂等路径掩盖 Recovery Decision 数据异常。

## 边界

- Trace 仍然不是 Recovery source of truth；
- PostgreSQL NodeExecution / Checkpoint 仍是 Durable Recovery 数据源；
- 不创建第二套 Planner；
- 不新增 Migration；
- 只强化现有 Decision Trace 的一致性 Contract。

## Unit Test

新增覆盖：

- 相同 Decision payload 幂等返回已有 event；
- 已有 event 的 frontier 与当前 Planner 结果不一致时拒绝；
- 保持原有无 trace identity 与新 Decision 持久化测试。

当前环境未执行仓库本地 pytest，因此不得记录 Unit Test 为 PASS。
