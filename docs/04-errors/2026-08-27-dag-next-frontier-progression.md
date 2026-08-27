# 2026-08-27 DAG Next Frontier Durable Progression

## 问题

Multi-frontier Runtime 已经能够在所有 Branch Node-level Checkpoint 成功后写入 Execution-level `frontier_completed` Checkpoint，但 Checkpoint 之后“重新使用唯一 DAG Planner 计算下一 Frontier，并生成 Durable Frontier identity”的职责没有独立的正式适配边界。

如果调用方直接从当前 Branch Node 推导下一 Node，条件分支与 Join 的 decision fingerprint 可能与正式 Planner 漂移；如果直接把下一 Frontier 写入数据库，又会绕过现有 `complete_frontier_with_checkpoint()` 的统一 Frontier → Checkpoint → Next Frontier 事务 Contract。

## 根因

现有职责已经分别存在：

- `WorkflowDagResumePlanner`：唯一 DAG completed facts / frontier / predecessor / decision fingerprint 计算入口；
- `WorkflowDagResumeRuntimePlanner`：Runtime frontier 消费计划；
- `WorkflowExecutionCheckpointService`：Execution-level durable Checkpoint；
- `complete_frontier_with_checkpoint()`：Frontier → Checkpoint → Next Frontier 原子持久化；
- `WorkflowFrontierIdentity`：Durable Frontier 幂等身份。

缺少的是把“Checkpoint 后的 completed facts → Planner → Frontier identity”串起来的纯领域适配层。

## 修复

新增 `WorkflowDagFrontierProgressionService`：

```text
Branch Node Checkpoint completed
        ↓
frontier_completed Checkpoint
        ↓
WorkflowDagFrontierProgressionService
        ↓
WorkflowDagResumePlanner
        ↓
next frontier + decision fingerprint
        ↓
WorkflowFrontierIdentity
        ↓
existing complete_frontier_with_checkpoint()
```

该模块只负责规划，不执行 Node、不写 Checkpoint、不获取 Worker ownership；真正持久化仍必须进入既有 Frontier progression Contract。

## 不变量

1. 当前 frontier 的全部 Node 必须已经存在于 completed durable facts；
2. `state_data_by_node` 只能包含已完成 Node；
3. 下一 Frontier 必须重新由唯一 `WorkflowDagResumePlanner` 计算；
4. 下一 Frontier identity 使用 Planner 的 deterministic decision fingerprint；
5. 没有下一 Frontier 时返回 terminal 结果，不创建虚假的 Frontier；
6. 不新增第二套 DAG Planner、Merge、Checkpoint 或 Frontier Repository。

## Unit Test

`backend/tests/unit/test_workflow_dag_frontier_progression.py` 覆盖：

- 多 frontier 下一批 Node 的 deterministic identity；
- terminal DAG 不创建 Next Frontier；
- 当前 frontier 未形成完整 durable facts 时拒绝 progression。

当前环境未执行 pytest，因此不得记录为 PASS。
