# Phase 2.7 Decision Fingerprint Replay Consistency

## 问题

`workflow.dag.frontier_decided` 原有 `decision_id` 只绑定 Execution、completed Node、frontier 和 selected predecessor，没有绑定实际参与 Conditional Evaluation 的持久化 source state。

因此理论上可能出现：

```text
同一 execution
+ 同一 completed nodes
+ 同一 frontier
+ 同一 selected predecessor
+ 不同 condition source state
        ↓
旧 decision_id 与新 decision_id 相同
```

这会削弱 Recovery 后 decision replay 的对账能力。

## 根因

Decision Trace 在 Runtime 层计算 hash，而 Planner 才是唯一掌握完整 frontier 计算输入的位置。Runtime 没有条件 source state，因此无法自行形成完整 deterministic fingerprint。

## 修复

将 `decision_fingerprint` 计算责任收敛到 `WorkflowDagResumePlanner`：

1. 绑定冻结 DAG Node ID；
2. 绑定持久化 `completed_node_ids`；
3. 绑定 frontier；
4. 绑定 selected predecessor；
5. 仅绑定实际参与条件判断的 completed source state；
6. 使用稳定 JSON canonicalization + SHA-256；
7. Runtime 只消费 Planner fingerprint 并写入 Trace。

业务 `state_data` 仍然不直接写入 Trace。

## 结果

```text
同一 durable snapshot
        ↓
相同 fingerprint

Condition source state 改变
        ↓
重新计算
        ↓
不同 fingerprint
```

因此 Recovery 后可以用 fingerprint 判断 Conditional Decision 是否仍然对应同一 durable fact snapshot。

## 测试

新增 Unit Test：

`backend/tests/unit/test_workflow_dag_decision_fingerprint.py`

覆盖：

- 相同 durable facts、不同 Mapping 插入顺序 → fingerprint 相同；
- Conditional state 改变 → frontier 改变且 fingerprint 不同。

当前未在本环境实际执行 pytest，因此不得标记测试 PASS。