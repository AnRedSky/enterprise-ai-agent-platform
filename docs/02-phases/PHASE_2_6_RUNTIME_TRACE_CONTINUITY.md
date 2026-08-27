# Phase 2.6 Runtime Trace Continuity

> 状态：**开发中 / 收口阶段**
> 基线：`main`
> 日期：2026-08-27

## 本轮完成

本轮完成 Worker claim / lease 的过期 running Execution 回收边界。Worker 现在不仅消费 pending Execution，还可以在旧 Worker 租约已经过期时，通过 PostgreSQL 行锁原子接管遗留 running Execution，并把它重新置为 pending 后交给新的 Worker owner 执行。

```text
旧 Worker
    │
    │ lease expires
    ↓
running Execution
    │
    │ PostgreSQL row lock
    ↓
新 Worker claim
    │
    ├── status = pending
    ├── worker_owner = new owner
    ├── worker_attempt += 1
    └── current_node_id 清空
    ↓
WorkflowExecutionService
    ↓
ownership fencing
    ↓
WorkflowRuntime
```

这解决了此前 `running + expired lease` 无法重新进入 Worker claim 队列的问题。

## Scheduler Recovery Trace 生命周期

```text
WorkflowRecoveryScheduler.scan_once()
        ↓
WorkflowSchedulerTraceService.start_scan()
        ↓
failed Execution candidates
        ↓
WorkflowExecutionAutomaticRecoveryService.recover(
    parent_trace_id=scheduler_trace_id
)
        ↓
Automatic Recovery child trace
        ↓
Resume + durable Recovery Trace Link
        ↓
WorkflowSchedulerTraceService.finish_scan()
```

Scheduler Scan 的 `started / scan.completed / finished` 事件继续共享父级 `trace_id`。每个 Automatic Recovery 使用独立 child `trace_id`，并在 `workflow.recovery.trace.*` 与 `workflow.recovery.attempt` 事件中携带 `parent_trace_id`。

## Trace Contract

`WorkflowRecoveryEvent` 使用：

- `parent_trace_id`：标识当前 Recovery trace 的父级 Scheduler trace；
- `trace_id`：当前事件所属的 Recovery / Scheduler trace；
- `execution_id` / `resume_execution_id`：执行身份关联。

该字段只用于控制面 lineage，不承载业务 state。

## Worker Lease / Fencing Contract

```text
pending + 无 owner
        │
        ▼
Worker A claim
        │
        ├── owner = A
        └── lease = T1

running + lease(T1) 过期
        │
        ▼
Worker B claim（行锁）
        │
        ├── status → pending
        ├── owner → B
        └── attempt + 1

Worker A 后续状态转换
        │
        ▼
WorkflowExecutionService ownership fencing
        │
        └── 拒绝旧 owner
```

Contract 规则：

1. 只有 `pending` 或 `running + lease 已过期` 的 Execution 可以进入 claim；
2. claim 必须使用 PostgreSQL 行锁，避免多个 Worker 同时接管同一 Execution；
3. 回收过期 `running` Execution 时必须先回到 `pending`，再写入新的 Worker owner；
4. `worker_attempt` 每次新的 claim 都递增；
5. 旧 Worker 的 owner 与新 owner 不一致时，`WorkflowExecutionService` 必须拒绝旧 Worker 的 Node / Execution 状态推进；
6. lease 到期本身不能授予旧 Worker 继续提交状态的权限；
7. 当前回收动作不清除已有 `WorkflowNodeExecution` 事实，后续 Worker 接管阶段继续通过 orphaned running Node recovery 收敛节点状态；
8. Worker lease 字段仍必须满足现有数据库约束，terminal Execution 不允许残留 owner / lease。

## Runtime 边界

```text
WorkflowRuntime
├── Join Node
│   └── 只执行已由 Join Readiness Contract 验证的 merged state
│
└── Recovery Trace Continuity
    ├── 读取持久化 trace identity
    ├── 不读取 trace data payload
    ├── 不修改 Resume input_data
    └── 不新增 Trace / Checkpoint 数据表
```

Join 继续复用基础 Runtime 的 Retry、Timeout、CircuitBreaker、NodeExecution 与 Checkpoint 事务边界；Join 不调用 Model Provider。

## 当前完整链路

```text
Scheduler Scan
    │
    │ trace_id = S
    ↓
Automatic Recovery
    │
    │ trace_id = R
    │ parent_trace_id = S
    ↓
Resume Execution
    │
    ↓
Persistent Recovery Trace Link
    │
    │ trace_id = R
    ↓
Worker claim
    │
    ├── pending claim
    │
    └── expired running reclaim
    │
    ↓
Lease / Fencing
    │
    ↓
WorkflowRuntime
    │
    ↓
DAG Branch
    │
    ↓
Join
    │
    ↓
Checkpoint
    │
    ↓
Execution Completed
```

## Unit Test

新增：

```text
backend/tests/unit/test_workflow_worker_lease_reclaim.py
```

覆盖：

1. 过期 `running` Execution 可以被新 Worker 回收；
2. 回收后状态重新进入 `pending`；
3. owner 被替换且 `worker_attempt` 递增；
4. `current_node_id` 在 Execution 回收边界清空；
5. 普通 `pending` claim 行为保持兼容；
6. 没有可消费 Execution 时保持原有返回语义。

当前仅保留 Unit Test 验证范围。Backend Full Regression、Real API、E2E、Release Gate 暂停；**未实际执行的测试不得记录 PASS**。

## 当前主线

```text
Scheduler parent trace
        ↓
Automatic Recovery child trace
        ↓
Resume Trace Link
        ↓
Worker claim / expired lease reclaim
        ↓
Ownership fencing
        ↓
Worker / Runtime child trace
        ↓
Checkpoint durable facts
        ↓
Phase 2.6 Closure
```

下一步不再扩展 Trace 抽象，继续收口 **lease loss 后旧 Worker 的主动执行中止语义**：heartbeat 检测 ownership 失效后必须让 Runtime 停止推进，而不是仅等待下一次数据库状态转换才被动发现 fencing；随后完成 Phase 2.6 Closure。
