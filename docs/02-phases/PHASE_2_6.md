# Phase 2.6 — Durable Execution Checkpoint Foundation

> 状态：**开发中**；本阶段先建立可审计、不可变的 Execution Checkpoint 持久化基础，不在本阶段隐式实现自动 Resume、Saga 或跨节点补偿。
> 评估日期：2026-08-26
> 优先级：**P1**

## 1. 目标

在 Phase 2.5 已完成 Scheduler / Worker / Runtime 进程与 ownership 边界的基础上，为后续 durable execution 建立唯一的 Checkpoint 持久化边界：

```text
Worker claim / ownership fencing
        ↓
WorkflowExecutionService
        ↓
Checkpoint Service
        ↓
PostgreSQL immutable checkpoint
        ↓
后续 Durable Resume / Recovery
```

Checkpoint 是持久化事实，不承担调度、状态机推进或 Worker ownership 决策。

## 2. 本阶段实现

- Migration `0032_workflow_execution_checkpoint`；
- `WorkflowExecutionCheckpoint` 持久化模型；
- `WorkflowExecutionCheckpointService`；
- Execution 内唯一 `sequence`；
- `latest()` 正式读取入口；
- Checkpoint 只追加、不覆盖历史快照；
- 记录 Execution / Node 状态、attempt、业务 state、输入输出、错误与 Worker owner；
- 单元测试覆盖追加、参数边界与最新快照读取。

## 3. 设计边界

### Checkpoint 负责

- 保存可恢复的业务状态快照；
- 保存 Node / Execution 当前状态上下文；
- 保存产生快照时的 Worker owner；
- 保留历史版本，支持后续恢复与审计。

### Checkpoint 不负责

- 不自动把 `running` Execution 改回 `pending`；
- 不执行 Runtime；
- 不绕过 ownership fencing；
- 不修改 Node 状态机；
- 不决定 Retry / Circuit Breaker；
- 不实现 Saga / compensation；
- 不直接提供 HTTP Resume 接口。

## 4. 数据不变量

```text
execution_id + sequence 唯一
Checkpoint 只追加，不覆盖
sequence 由调用边界明确分配
state_data 表示可持久化业务状态，不代表自动恢复授权
worker_owner 只记录事实，不用于恢复时自行复活 ownership
```

## 5. 下一步

1. 开发者执行 `0032` migration 与 Checkpoint targeted tests；
2. 在 WorkflowRuntime 的明确 Node completion boundary 接入 Checkpoint append；
3. 补充真实 PostgreSQL Checkpoint persistence Gate；
4. 设计并实现 durable resume 的 ownership / version / idempotency 约束；
5. 仅在上述边界稳定后再开放自动恢复。
