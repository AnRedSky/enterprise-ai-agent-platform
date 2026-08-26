# Phase 2.5 — Scheduler → Worker 执行解耦

> 状态：**代码实现完成；Worker ownership fencing、orphaned running Node recovery、Scheduler/Worker Recovery Acceptance 已进入本地验收闭环；当前继续进行 lease ownership 边界硬化。**
> 评估日期：2026-08-26
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
- `run_worker.py` 与独立 Worker entrypoint；
- PostgreSQL `FOR UPDATE SKIP LOCKED` claim；
- Worker 复用唯一 `WorkflowExecutionService` / `WorkflowRuntime`；
- Worker ownership fencing；
- Lease heartbeat；
- Worker 执行超时边界；
- HTTP `/run` 与 Worker Runtime 竞争边界；
- Runtime 前 `pending Execution + orphaned running Node` recovery；
- Node 状态机继续禁止 `running → running`；
- Tenant Safe Real API helper 支持显式多个合法业务 HTTP 结果；
- Heartbeat 瞬态数据库异常重试；
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
Scheduler
     ↓
PostgreSQL pending Execution
     ↓
Worker claim + lease + ownership fencing
     ↓
Recovery Boundary
     ↓
Lease Heartbeat（仅续未过期 lease）
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

## 4. Worker Recovery Boundary

Worker claim 后、Runtime 开始前检查当前 `pending Execution` 是否存在遗留 `running Node`：

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

Heartbeat 续租的正式条件为：

```text
Execution 存在
AND worker_owner == 当前 Worker
AND Execution 非终态
AND worker_lease_expires_at > now
```

其中 `worker_lease_expires_at > now` 是必要条件，而不是日志诊断条件。lease 一旦到期，ownership 即视为失效；旧 Worker 即使仍看到相同 `worker_owner`，也不得自行恢复 lease。

```text
lease 未过期
    ↓
heartbeat 可以 renew

lease 已过期
    ↓
heartbeat 退出
    ↓
ownership fencing 阻止旧 Runtime 后续写入
```

瞬态数据库异常仍允许 heartbeat 进入下一轮重试，但不能通过无限重试突破 lease 的实际时间边界。

## 6. 当前执行链

```text
API → Trigger Domain → Scheduler → pending Execution
                                      ↓ PostgreSQL
                              Worker claim + lease
                                      ↓
                           recovery / ownership fence
                                      ↓
                           lease heartbeat
                                      ↓
                           WorkflowExecutionService
                                      ↓
                              WorkflowRuntime
```

## 7. 当前开发者本地结果

此前开发者已反馈：

### Worker ownership Unit

```text
9 passed in 1.16s
```

### Backend Regression

```text
413 passed, 3 skipped, 36 deselected in 29.51s
35 passed in 67.73s
```

### Scheduler / Worker Recovery Acceptance

```text
1 passed in 8.67s
```

以上为本轮 lease expiry hardening 之前的实际结果。本轮新增 heartbeat / lease expiry 测试后，必须重新执行对应 Gate 才能形成新的最终验收记录。

## 8. 当前风险边界

Worker lease 继续承担消费 ownership 与 Runtime 状态转换 fencing。Runtime 已进入 `running` 后 Worker 崩溃时，本阶段仍不新增自动 resume；后续 durable execution / checkpoint 单独处理。

## 9. 下一步

1. 开发者拉取最新 `main` 后执行 Worker targeted tests；
2. 执行 Tenant Safe Real API；
3. 执行 Backend Regression Gate；
4. 执行只读 Worker Runtime consistency diagnostic；
5. 执行 Scheduler / Worker Recovery Acceptance；
6. 根据实际结果关闭 Phase 2.5 Acceptance，或继续处理真实失败边界。
