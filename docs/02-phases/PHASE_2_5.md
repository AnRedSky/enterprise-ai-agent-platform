# Phase 2.5 — Scheduler → Worker 执行解耦

> 状态：**已完成**；Scheduler / Worker 进程边界、Worker ownership fencing、orphaned running Node recovery、lease heartbeat 与真实 PostgreSQL recovery acceptance 已形成闭环。
> 完成日期：2026-08-26
> 优先级：**P1**

## 1. 目标

在 Phase 2.4 API Service / Scheduler Service 独立进程边界基础上完成：

```text
Scheduler = 产生执行任务
Worker   = 消费执行任务
Runtime  = 唯一执行实现
```

## 2. 已实现

- Scheduled Trigger 只创建 `status=pending` 的 `WorkflowExecution`；
- 保留 `schedule_slot_key = WorkflowExecution.idempotency_key`；
- Worker lease migration `0029_workflow_worker_lease`；
- `WorkflowWorker` 领域模块；
- `run_worker.py` 独立 Worker entrypoint；
- PostgreSQL `FOR UPDATE SKIP LOCKED` claim；
- Worker 复用唯一 `WorkflowExecutionService` / `WorkflowRuntime`；
- Worker ownership fencing；
- Lease heartbeat：首轮立即检查，后续周期续租；
- Worker 执行超时边界；
- HTTP `/run` 与 Worker Runtime 竞争边界；
- Runtime 前 `pending Execution + orphaned running Node` recovery；
- Node 状态机继续禁止 `running → running`；
- Tenant Safe Real API claim-race helper；
- Lease 到期后禁止旧 Worker heartbeat 复活 ownership。

## 3. 产品级执行架构

完整产品设计记录：

```text
docs/00-architecture/WORKFLOW_WORKER_EXECUTION_ARCHITECTURE.md
```

核心链路：

```text
API / Trigger
     ↓
Scheduler Service
     ↓
PostgreSQL pending Execution
     ↓
Worker claim + lease + ownership fencing
     ↓
Recovery Boundary
     ↓
Lease Heartbeat（首轮立即检查，后续周期续租）
     ↓
WorkflowExecutionService
     ↓
WorkflowRuntime
     ↓
Node / Execution terminal state
     ↓
Audit / Trace / ownership cleanup
```

职责冻结为：**Scheduler 负责“什么时候执行”，Worker 负责“执行什么”，Runtime 负责“如何执行节点”。**

## 4. Recovery Boundary

```text
pending Execution + running Node
        ↓
WORKER_RECOVERY_INTERRUPTED
        ↓
running → failed
        ↓
既有 failed → running 合法入口
        ↓
WorkflowRuntime retry policy
```

本机制不放宽状态机、不复制 Runtime retry 算法，也不实现 `running Execution` checkpoint/resume。

## 5. Lease Ownership Boundary

Heartbeat 的正式条件：

```text
Execution 存在
AND worker_owner == 当前 Worker
AND Execution 非终态
AND worker_lease_expires_at > now
```

Heartbeat 时序：

```text
heartbeat task 创建
    ↓
立即 renew / ownership check
    ├── ownership 失效 → 立即退出
    ├── 瞬态数据库异常 → 记录日志 → sleep(interval) → 重试
    └── renew 成功 → sleep(interval) → 下一轮
```

首轮立即检查是 ownership 生命周期的一部分；周期 interval 只控制下一轮调度。

## 6. 本地验收结果

### Worker targeted Unit

```text
13 passed in 1.23s
```

### Backend Regression Gate

```text
417 passed, 3 skipped, 36 deselected in 29.44s
```

### Tenant Safe Real API

```text
35 passed in 63.01s
```

### Scheduler / Worker Recovery Acceptance

此前已完成真实 PostgreSQL recovery 验收：

```text
1 passed
```

### 数据库

```text
0031_usage_provider_lifecycle
```

上述结果均来自开发者本地实际执行，不使用 GitHub Actions 结果替代。

## 7. 风险边界

Worker lease 继续承担消费 ownership 与 Runtime 状态转换 fencing。Runtime 已进入 `running` 后 Worker 崩溃时，本阶段不自动 resume；checkpoint / durable resume 进入独立 Phase 2.6。

## 8. Closure

Phase 2.5 不再继续扩展 Worker Runtime 语义。后续主线进入：

```text
Phase 2.6 — Durable Execution Checkpoint Foundation
```
