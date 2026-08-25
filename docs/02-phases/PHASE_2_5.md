# Phase 2.5 — Scheduler → Worker 执行解耦

> 状态：**代码实现完成；核心 Backend / Migration / Real API / Scheduler Recovery Acceptance 已由开发者本地实际验证通过。**
> 评估日期：2026-08-25
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
- HTTP `/run` 与 Worker Runtime 竞争边界；
- Node 状态机继续禁止 `running → running`；
- Tenant Safe Real API helper 支持显式多个合法业务 HTTP 结果。

## 3. 当前执行链

```text
API → Trigger Domain → Scheduler → pending Execution
                                      ↓ PostgreSQL
                              Worker claim + lease
                                      ↓
                           ownership fenced Runtime
```

## 4. 开发者本地实际结果

### Worker ownership Unit

```text
7 passed in 0.92s
```

### Migration

```text
0031_usage_provider_lifecycle (head)
```

### Tenant Safe Real API

```text
35 passed in 61.53s
35 passed in 65.24s
```

### Backend Regression Gate

```text
411 passed, 3 skipped, 36 deselected in 29.70s
Tenant Safe Real API: 35 passed in 57.33s
[PASS] Backend regression gate completed.
```

### Scheduler / Worker Recovery Acceptance

```text
1 passed in 9.55s
[PASS] Scheduler / Worker recovery acceptance completed.
```

## 5. Worker 手工运行日志边界

直接运行 Worker 时出现的：

```text
503 Circuit Breaker is open
404 Mock provider HTTP 404
504 Retry backoff exceeds workflow deadline
```

属于已有负向业务路径，不应由 Worker 吞掉。

```text
409 Node 不允许从 running 到 running
```

仍属于必须禁止的非法状态转换，不能通过放宽状态机掩盖重复 Runtime。

本轮新增只读一致性诊断：

```text
backend/scripts/dev/inspect_worker_runtime_consistency.py
backend/scripts/dev/worker_runtime_consistency.ps1
```

用于确认数据库是否存在：

```text
pending Execution + running Node
```

当前阶段禁止自动 resume / 自动重置 running Node。

## 6. 当前风险边界

Worker lease 继续承担消费 ownership 与 Runtime 状态转换 fencing。Runtime 已进入 `running` 后 Worker 崩溃时，本阶段仍不新增自动 resume；后续 durable execution / checkpoint 单独处理。

## 7. 当前结论

Phase 2.5 的核心代码与本地核心验收已经完成。剩余工作不是继续修改 Node 状态机，而是执行一致性诊断并根据真实 Execution ID / Worker owner 判断 `running → running` 日志是否来自遗留持久化异常。
