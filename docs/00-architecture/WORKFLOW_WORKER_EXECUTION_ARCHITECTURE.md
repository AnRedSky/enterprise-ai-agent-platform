# Worker 执行架构产品设计记录

> 适用版本：Phase 2.5 / Phase 2.6
> 更新日期：2026-08-26
> 架构基线：`main`

## 1. 产品级执行职责

Workflow 的异步执行采用明确的服务边界：

```text
API Service
    ↓ 创建 / 管理 WorkflowExecution
Scheduler Service
    ↓ 负责何时执行
PostgreSQL pending WorkflowExecution
    ↓
Worker Service
    ↓ 负责执行什么
WorkflowExecutionService
    ↓
WorkflowRuntime
    ↓
Node completion boundary
    ↓
Checkpoint Service
    ↓
PostgreSQL immutable checkpoint
```

产品职责必须保持：

- **API Service**：提供 Workflow、Trigger、Execution 管理接口，不直接承担后台持续消费。
- **Scheduler Service**：负责 `next_run_at`、slot、lease、misfire 和幂等决策，只产生 `pending WorkflowExecution`，不直接调用 WorkflowRuntime。
- **Worker Service**：负责消费 `pending WorkflowExecution`，执行 claim、lease heartbeat、ownership fencing、恢复边界和 Runtime 调用。
- **WorkflowExecutionService**：唯一 Execution / Node 状态机入口，负责状态转换、治理审计、ownership fencing 以及 Node completion 的 Checkpoint 原子写入。
- **WorkflowRuntime**：唯一 Workflow Node 执行实现，负责 retry、timeout、circuit breaker、Provider/Tool 等实际业务执行。
- **Checkpoint Service**：只保存已经发生的执行事实，不执行 Runtime，不决定恢复，不修改状态机。

## 2. Worker 完整执行流程

```text
Scheduler / Manual / Webhook
          ↓
PostgreSQL Execution = pending
          ↓
Worker claim
          ↓
worker_owner + lease + attempt
          ↓
Ownership fencing
          ↓
Recovery Boundary
pending + orphaned running Node
          ↓
Lease Heartbeat
首轮立即检查 / 后续周期续租
          ↓
WorkflowExecutionService.run
          ↓
WorkflowRuntime
          ↓
Node pending/failed → running
          ↓
Node execution
      ┌───┴────┐
      ↓        ↓
   failed   completed
      │        │
      │        ↓
      │   Checkpoint Service
      │        ↓
      │   append next sequence
      │        ↓
      │   same DB transaction
      │        ↓
      └────→ terminal / next node
```

## 3. Checkpoint 原子事务边界

Node 成功完成时，正式持久化边界为：

```text
transition_node(..., completed)
       ↓
Node status = completed
       ↓
Checkpoint sequence = max(sequence) + 1
       ↓
Checkpoint state_data / node / worker_owner snapshot
       ↓
flush
       ↓
db.commit()
```

因此 Node 与 Checkpoint 是同一数据库事务的一部分：

```text
成功：Node completed + Checkpoint 同时提交
失败：事务整体回滚，不留下半完成 Checkpoint
```

`execution_id + sequence` 使用 PostgreSQL 唯一约束保证历史 Checkpoint 不可覆盖。

当前 `sequence` 在 Execution 已被 `FOR UPDATE` 锁定后计算，因此与现有 Worker ownership fencing / Execution transition 边界一致。

## 4. Checkpoint 数据语义

Checkpoint 保存：

```text
execution_id
sequence
execution_status
node_id
node_attempt
node_status
state_data
input_data
output_data
worker_owner
error_code
error_message
created_at
checkpoint_reason
```

其中：

```text
state_data = 后续恢复可能需要的业务状态
worker_owner = 当时事实快照，不代表未来恢复时可重新取得 ownership
```

Checkpoint 是追加日志，不允许覆盖历史快照。

## 5. Recovery 边界

当前 Worker recovery 仍只处理：

```text
pending Execution + orphaned running Node
        ↓
WORKER_RECOVERY_INTERRUPTED
        ↓
running → failed
        ↓
Runtime 使用既有 failed → running 合法入口
```

Checkpoint 不改变这一规则。

已经进入 `running Execution` 后 Worker 崩溃时的 durable resume、checkpoint restore、Saga、compensation 仍属于后续独立阶段。

## 6. Lease Heartbeat

Heartbeat 正式规则：

```text
heartbeat task 创建
    ↓
立即 renew / ownership check
    ├── success → sleep(interval)
    ├── transient DB error → sleep(interval) → retry
    ├── lease expired → exit
    └── ownership lost / terminal → exit
```

Checkpoint 不延长 lease，也不改变 ownership fencing。

## 7. Manual `/run` 与 Worker 竞争

```text
POST create → pending
      ├──────── Worker claim → running
      │
      └──────── POST /run → 409 只有 pending Execution 可以 Run
```

Checkpoint 只在真实 Runtime Node completion 边界产生，不允许 HTTP `/run` 因 Checkpoint 存在而重复进入 Runtime。

## 8. 产品可靠性边界

Phase 2.5 已完成：

- Scheduler / Worker 独立进程边界；
- Worker claim；
- lease heartbeat；
- ownership fencing；
- orphaned running Node recovery；
- Manual `/run` claim race fencing；
- `running → running` 持续非法。

Phase 2.6 当前新增：

- immutable Checkpoint model；
- Node completed transactional Checkpoint append；
- PostgreSQL sequence uniqueness；
- latest Checkpoint read boundary。

仍未实现：

- running Execution 自动恢复；
- HTTP Resume；
- Saga / compensation；
- 跨版本 Resume migration；
- Checkpoint garbage collection / retention policy。

## 9. 下一阶段设计重点

正式实现 durable resume 前必须先确定：

1. Resume 只能由新的 Worker owner 执行；
2. Checkpoint 对应的 Workflow Version 必须可验证；
3. Resume 必须具备 idempotency key，避免重复副作用；
4. 恢复入口必须经过既有 Execution / Node 状态机；
5. 不能根据历史 `worker_owner` 自动复活旧 Worker ownership；
6. Provider / Tool 等非幂等副作用必须有明确 replay policy。
