# 2026-08-27 Multi-frontier Join Recovery 边界

## 问题

Durable Frontier 的 Multi-frontier Branch 成功后会写入 `frontier_completed` Execution-level Checkpoint，并把所有 Branch output 合并为 Join 输入。Recovery Bootstrap 原先只根据 completed Node facts 重新运行 Planner，没有验证该 Execution-level merged state 是否仍与当前 Planner 选定 predecessor 的 durable output 一致。

这会留下一个 Recovery 完整性缺口：Checkpoint state 如果发生 payload drift，Recovery 仍可能把它当作 Join 输入继续执行，导致 Recovery 使用的 merged state 与 PostgreSQL Durable Node facts 不一致。

## 根因

`frontier_completed` 是 Execution-level snapshot，不绑定单个 NodeExecution。它不能通过 `assert_node_fact_complete()` 校验，因此 Join Recovery 必须把：

```text
Source Checkpoint state
        ↕
Planner selected predecessors
        ↓
completed Node durable outputs
        ↓
唯一 State Merge
```

重新建立一致性证明。

## 修复

新增 `WorkflowDagJoinRecoveryService`：

- 只消费调用方已经读取的 Definition、completed Node facts、Planner selected predecessor 与 Checkpoint state；
- 复用唯一 `WorkflowDagJoinReadinessService`，不复制 DAG 条件求值或 State Merge 算法；
- 从 durable predecessor output 重新计算 Join merged state；
- `frontier_completed` Checkpoint state 与重新计算结果不一致时立即拒绝 Recovery；
- 任一 selected predecessor 尚未完成时拒绝 Join Recovery；
- 全流程纯内存、无数据库读取、无 Runtime 启动、无 commit、无状态修改。

`WorkflowExecutionResumeBootstrapService` 在 Recovery 计算首个 Planner frontier 后，仅当最新 Checkpoint 为 `frontier_completed` 且首个 frontier 包含 `join` Node 时启用该校验。这样普通 Node Recovery 不增加额外边界，Multi-frontier Join Recovery 则获得完整的 merged state lineage guard。

## 一致性边界

```text
Source Execution Checkpoint
        ↓
Resume Bootstrap
        ↓
completed Node durable facts
        ↓
WorkflowDagResumePlanner
        ↓
selected predecessor snapshot
        ↓
WorkflowDagJoinReadinessService
        ↓
merged state rebuild
        ↓
Checkpoint state equality guard
        ↓
Join Recovery frontier
```

Trace / Decision metadata 仍只用于审计与 Replay Guard；Recovery source of truth 继续是 PostgreSQL Durable Node / Checkpoint facts。

## 测试

新增 `backend/tests/unit/test_workflow_dag_join_recovery.py`，覆盖：

- 从 durable predecessor facts 重建 Join merged state；
- Checkpoint merged state drift 拒绝；
- 输入 state 不可变；
- predecessor 未完成时拒绝。

当前环境无法本地执行 pytest，因此本提交不记录 Unit Test PASS；按开发准则仅保留待本地执行状态。
