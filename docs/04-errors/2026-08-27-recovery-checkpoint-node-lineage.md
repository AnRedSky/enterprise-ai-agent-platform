# 2026-08-27 Recovery Checkpoint Node Lineage

## 问题

Recovery 路径在读取最新 Checkpoint 时原先使用普通 `latest()`，而不是已经提供 Node Fact 完整性校验的 `latest_recovery_fact()`。

这意味着一个 `node.completed` Checkpoint 如果与同一 Execution 的 `WorkflowNodeExecution` 在 `status / attempt / output_data` 上发生漂移，Recovery Candidate 仍可能被生成，进而把不一致的 Durable Snapshot 交给 Resume Bootstrap。

## 根因

Checkpoint 的恢复边界不仅由 `checkpoint_reason`、Execution status 和 Worker ownership 决定，还必须证明 Node-level Checkpoint 与对应 Durable Node Fact 是同一个不可变执行事实。

`WorkflowExecutionCheckpointService` 已提供 `assert_node_fact_complete()` 与 `latest_recovery_fact()`，但 Automatic Recovery 与 Resume Contract 尚未统一使用该恢复专用读取入口，导致“定义了 invariant，但主恢复路径没有强制执行”的缺口。

## 修复

- Automatic Recovery `evaluate()` 改用 `latest_recovery_fact()`；
- Resume Contract `resume_with_outcome()` 改用 `latest_recovery_fact()`；
- 两条正式 Recovery 路径都继续传递当前 Execution 的 `tenant_id`；
- `frontier_completed` Execution-level Checkpoint 不绑定 Node Fact，因此保持原有恢复行为；
- 不增加第二套 Checkpoint 校验逻辑，继续复用单一 `WorkflowExecutionCheckpointService`。

## Durable 边界

```text
latest Checkpoint
      ↓
node_id != None ?
      ↓ yes
same Execution Node Fact
  ├─ status
  ├─ attempt
  └─ output_data
      ↓
Recovery Candidate
      ↓
Resume
```

如果 Node-level Checkpoint 与 Durable Node Fact 不一致，Recovery 应立即失败，而不是生成新的 Resume Execution。

## 后续

Resume Checkpoint sequence / Source checkpoint lineage 的完整语义仍属于 Recovery / Replay Closure 后续任务；本次只收紧“Recovery 读取 Snapshot 时必须先验证 Node Fact”的既有安全边界。