# Phase 2.6 — Durable Execution Checkpoint Foundation

> 状态：**开发中**；Checkpoint 已接入 WorkflowExecutionService 的 Node completed 边界，并与 Node 状态转换共享同一数据库事务；尚未实现自动 Resume、Saga 或跨节点补偿。
> 评估日期：2026-08-26
> 优先级：**P1**

## 1. 目标

在 Phase 2.5 已完成 Scheduler / Worker / Runtime 进程与 ownership 边界的基础上，为后续 durable execution 建立唯一 Checkpoint 持久化边界：

```text
Worker claim / ownership fencing
        ↓
WorkflowExecutionService
        ↓
Node transition
        ↓
Checkpoint Service
        ↓
PostgreSQL immutable checkpoint
        ↓
后续 Durable Resume / Recovery
```

Checkpoint 是持久化事实，不承担调度、状态机推进或 Worker ownership 决策。

## 2. 当前实现

- Migration `0032_workflow_execution_checkpoint`；
- `WorkflowExecutionCheckpoint` 持久化模型；
- `WorkflowExecutionCheckpointService.append()`；
- `WorkflowExecutionCheckpointService.append_next_in_transaction()`；
- `WorkflowExecutionCheckpointService.latest()`；
- Execution 内唯一 `sequence`；
- Checkpoint 只追加、不覆盖历史快照；
- `Node completed` 时自动追加 Checkpoint；
- Node 状态更新与 Checkpoint 追加在同一个数据库事务内提交；
- 记录 Execution / Node 状态、attempt、业务 state、输入输出、错误与 Worker owner；
- Checkpoint 集成单元测试；
- Real API + PostgreSQL Checkpoint persistence 验收测试入口。

## 3. 事务边界

Node 完成的正式边界为：

```text
Node pending/running
      ↓
WorkflowExecutionService.transition_node(..., completed)
      ↓
更新 Node 状态
      ↓
追加 sequence = max(sequence) + 1 的 Checkpoint
      ↓
flush
      ↓
同一 db.commit()
```

因此禁止出现：

```text
Node completed 已提交
Checkpoint 尚未提交
```

Checkpoint 服务在该路径中不独立 `commit`，而是加入调用方当前事务。

`execution_id + sequence` 由数据库唯一约束兜底；当前 Worker ownership fencing 已保证同一 Execution 的 Runtime 状态转换只由持有 owner 的执行者推进。

## 4. Checkpoint 负责

- 保存可恢复的业务状态快照；
- 保存 Node / Execution 当前状态上下文；
- 保存产生快照时的 Worker owner；
- 保留历史版本，支持后续恢复与审计。

## 5. Checkpoint 不负责

- 不自动把 `running` Execution 改回 `pending`；
- 不执行 Runtime；
- 不绕过 ownership fencing；
- 不修改 Node 状态机；
- 不决定 Retry / Circuit Breaker；
- 不实现 Saga / compensation；
- 不直接提供 HTTP Resume 接口。

## 6. 数据不变量

```text
execution_id + sequence 唯一
Checkpoint 只追加，不覆盖
sequence 在当前事务中按 Execution 现有最大序号递增
state_data 表示可持久化业务状态，不代表自动恢复授权
worker_owner 只记录事实，不用于恢复时自行复活 ownership
```

## 7. 下一步

1. 开发者验证新的 Runtime Checkpoint targeted tests；
2. 执行 Tenant Safe Real API / Backend Regression，确认没有破坏既有 Runtime、Worker 与 Provider 治理；
3. 验证 Real API + PostgreSQL Checkpoint persistence；
4. 设计 durable resume 的 ownership / version / idempotency 约束；
5. 仅在上述边界稳定后再开放自动恢复。
