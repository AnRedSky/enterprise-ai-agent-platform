# Worker 执行架构产品设计记录

> 适用版本：Phase 2.5
> 更新日期：2026-08-26
> 架构基线：`main`

## 1. 产品级执行职责

Workflow 的异步执行采用明确的三角色服务边界：

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
```

产品职责必须保持：

- **API Service**：提供 Workflow、Trigger、Execution 管理接口，不直接承担后台持续消费。
- **Scheduler Service**：负责 `next_run_at`、slot、lease、misfire 和幂等决策，只产生 `pending WorkflowExecution`，不直接调用 WorkflowRuntime。
- **Worker Service**：负责消费 `pending WorkflowExecution`，执行 claim、lease heartbeat、ownership fencing、恢复边界和 Runtime 调用。
- **WorkflowExecutionService**：唯一 Execution 状态机入口，统一处理 Execution / Node 状态转换、治理审计和租户边界。
- **WorkflowRuntime**：唯一 Workflow Node 执行实现，负责 retry、timeout、circuit breaker、Provider/Tool 等实际业务执行。

## 2. Worker 完整执行流程

```text
                    ┌──────────────────────┐
                    │ Scheduler / Manual   │
                    │ / Webhook Trigger    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ PostgreSQL           │
                    │ Execution = pending │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Worker claim         │
                    │ FOR UPDATE SKIP LOCKED│
                    └──────────┬───────────┘
                               │
                  owner + lease + attempt
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Ownership fencing    │
                    │ 当前 Worker 才可执行 │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Recovery Boundary    │
                    │ pending + running   │
                    │ Node → failed       │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Lease Heartbeat      │
                    │ 首轮立即检查/续租    │
                    │ 后续按 interval 周期 │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ ExecutionService.run │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ WorkflowRuntime      │
                    │ Node pending/failed  │
                    │ → running            │
                    └──────────┬───────────┘
                               │
                   ┌───────────┴───────────┐
                   ▼                       ▼
             completed                 failed
                   │                       │
                   └───────────┬───────────┘
                               ▼
                    ┌──────────────────────┐
                    │ Audit / Trace /      │
                    │ ownership cleanup    │
                    └──────────────────────┘
```

## 3. Claim 与 ownership

Worker 只能从 PostgreSQL 消费 `pending` Execution。claim 使用 PostgreSQL 行锁和 `FOR UPDATE SKIP LOCKED`，写入：

```text
worker_owner
worker_lease_expires_at
worker_attempt
```

同一 Execution 可以被多个 Worker 竞争，但只有最终持有 ownership 的 Worker 可以继续状态转换。旧 Worker 在 lease 失效或被接管后继续执行时，必须由 Execution ownership fencing 拒绝，而不是让旧 Runtime 继续修改数据。

## 4. Recovery Boundary

Worker 在正式进入 Runtime 前检查已经 claim 的 `pending Execution` 是否存在遗留 `running Node`：

```text
pending Execution
    +
Node status = running
    ↓
WORKER_RECOVERY_INTERRUPTED
    ↓
Node running → failed
    ↓
WorkflowRuntime 使用既有 failed → running 合法入口
```

该恢复边界解决 Worker 在 Node 已写入 `running` 后进程异常退出、Execution 仍保持 `pending` 时的持久化不一致。

**产品状态机不允许 `running → running`。** 状态机必须继续拒绝正常路径中的重复执行，以便发现并发 Runtime 或恢复边界错误。恢复逻辑不能复制 Runtime retry 算法，而是只负责把可证明的 Worker 中断状态重新收敛到合法状态。

## 5. Lease Heartbeat 与超时

Worker 执行长 Workflow 时独立刷新 lease，避免 Runtime 执行时间超过初始 lease 后被其他 Worker 错误接管。Runtime 外层同时受 Workflow deadline + 固定宽限控制，防止异常 Runtime 永久占用 Worker 消费协程。

Heartbeat 的单轮刷新属于可重试的基础设施操作，但 **lease 一旦到期即代表 ownership 已失效**：

```text
heartbeat task 创建
    ↓
立即 renew / ownership check
    ├── success + lease 未过期 → sleep(interval) → 下一轮
    ├── transient DB error → 记录日志 → sleep(interval) → 重试
    ├── lease 已过期 → heartbeat 退出
    └── ownership 不存在/Execution 已终态 → heartbeat 退出
```

续租查询必须同时满足 `worker_owner == 当前 Worker` 与 `worker_lease_expires_at > now`。不能仅凭残留 `worker_owner` 在 lease 到期后重新延长租约，否则旧 Worker 可能在 ownership 已失效后复活自己的 lease，破坏 claim / fencing 的时间边界。

首轮立即检查是 ownership 生命周期的一部分，而不是普通 polling 优化：Worker claim 后马上建立 heartbeat，必须立即确认当前 ownership 仍然有效；周期 `interval` 只控制成功检查后的下一次续租时间。这样可以避免短 lease、任务调度抖动或测试/进程调度延迟造成无意义的初始 ownership 暴露窗口。

这一区分非常重要：**瞬时数据库异常不能让 heartbeat task 静默死亡；ownership 已经失效也不能通过继续 heartbeat 伪造所有权。** Runtime 本身不因为单次 heartbeat 网络抖动被强制重置；若最终 lease 到期并被其他 Worker 接管，旧 Worker 后续状态写入必须由 ownership fencing 拒绝。

Heartbeat 与 Execution timeout 职责不同：

```text
lease heartbeat → 解决 ownership 生命周期
execution timeout → 解决执行时间上界
```

不得用延长 timeout 替代 ownership fencing，也不得用 polling 降低替代 lease。

## 6. Manual `/run` 与 Worker 竞争

创建 Execution 后，独立 Worker 可能先于 HTTP `/run` claim：

```text
POST create → pending
      ├──────────── Worker claim → running/completed
      │
      └──────────── POST /run → 409 只有 pending Execution 可以 Run
```

该 409 是合法业务竞态，不应修改为重复 Runtime。Real API 测试必须允许显式声明的合法结果，并继续通过真实 HTTP 查询验证最终 PostgreSQL 持久化状态。

## 7. 产品可靠性边界

当前 Phase 2.5 的 Worker 不实现 `running Execution` 的 checkpoint/resume。当前恢复能力仅覆盖：

```text
pending Execution + orphaned running Node
```

已经进入 `running Execution` 后 Worker 崩溃的 durable resume、checkpoint、Saga 等能力属于后续独立需求，不应通过本阶段隐式扩张。

## 8. 产品验收要求

必须同时验证：

1. Scheduler 不直接调用 Runtime；
2. Worker 可以独立 claim pending Execution；
3. claim 后 ownership fencing 生效；
4. Worker lease 可以持续刷新，且首轮立即检查、单次瞬态刷新异常不会永久终止 heartbeat；
5. lease 到期后旧 Worker 不能自行复活 lease；
6. pending + orphaned running Node 能在 Runtime 前恢复；
7. `running → running` 仍被状态机拒绝；
8. Worker 使用唯一 WorkflowExecutionService / WorkflowRuntime；
9. Manual `/run` 与 Worker claim 的 409 竞态不会产生第二个 Runtime；
10. Execution、Node、Audit、Trace 的 tenant / workflow / execution 关联保持一致；
11. Scheduler restart / Worker recovery 使用真实 PostgreSQL 链路验收。
