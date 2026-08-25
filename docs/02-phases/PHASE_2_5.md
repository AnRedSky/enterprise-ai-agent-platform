# Phase 2.5 — Scheduler → Worker 执行解耦

> 状态：**代码实现完成；Worker ownership fencing、orphaned running Node recovery、Scheduler/Worker Recovery Acceptance 已进入本地验收闭环。**
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
- Lease heartbeat；
- Worker 执行超时边界；
- HTTP `/run` 与 Worker Runtime 竞争边界；
- Runtime 前 `pending Execution + orphaned running Node` recovery；
- Node 状态机继续禁止 `running → running`；
- Tenant Safe Real API helper 支持显式多个合法业务 HTTP 结果。

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

## 5. 当前执行链

```text
API → Trigger Domain → Scheduler → pending Execution
                                      ↓ PostgreSQL
                              Worker claim + lease
                                      ↓
                           recovery / ownership fence
                                      ↓
                           WorkflowExecutionService
                                      ↓
                              WorkflowRuntime
```

## 6. 开发者本地实际结果

### Worker ownership Unit

最新开发者反馈：

```text
9 passed in 1.09s
```

覆盖 Worker recovery 与 ownership fencing。

### Migration

```text
0031_usage_provider_lifecycle (head)
```

### Backend Regression

最新开发者反馈：

```text
413 passed, 3 skipped, 36 deselected in 30.47s
```

但同一次 Gate 的 Tenant Safe Real API 仍有 1 个测试失败：

```text
test_circuit_breaker_half_open_probe_recovers_and_closes
POST /workflows/executions/{id}/run
→ 409 只有 pending Execution 可以 Run
```

该 409 与 Worker 独立 claim 竞态一致，不属于生产状态机缺陷。生产 `/run` Contract 不修改；本轮将该 Circuit Breaker Real API 测试统一接入既有 `run_or_observe_execution()` helper，显式观察合法 Worker claim race，并通过真实 HTTP 查询验证最终持久化状态。

因此在开发者重新执行 Gate 前，本 Acceptance 不记录为本轮最终 Passed。

## 7. 当前风险边界

Worker lease 继续承担消费 ownership 与 Runtime 状态转换 fencing。Runtime 已进入 `running` 后 Worker 崩溃时，本阶段仍不新增自动 resume；后续 durable execution / checkpoint 单独处理。

## 8. 下一步

1. 开发者拉取最新 main 后执行 Worker targeted tests；
2. 执行 Tenant Safe Real API，确认 Circuit Breaker probe 不再被合法 Worker claim race 阻塞；
3. 执行 Backend Regression Gate；
4. 执行只读 Worker Runtime consistency diagnostic；
5. 执行 Scheduler / Worker Recovery Acceptance；
6. 根据本轮实际结果更新 Acceptance / Project Status。
