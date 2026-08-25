# Phase 2.5 — Scheduler → Worker 执行解耦

> 状态：**代码已实现；本地 Backend / Migration / Real Acceptance 待开发者执行后汇总。**
> 评估日期：2026-08-25
> 优先级：**P1**

## 1. 目标

在 Phase 2.4 已完成 API Service / Scheduler Service 独立进程边界的基础上，继续完成：

```text
Scheduler = 产生执行任务
Worker   = 消费执行任务
Runtime  = 唯一执行实现
```

本阶段不重新设计 API Service / Scheduler Service 的进程边界。

## 2. 已实现

- `WorkflowTriggerService.invoke_scheduled()` 不再直接调用 `WorkflowExecutionService.run()`；
- Scheduled Trigger 只创建 `status=pending` 的 `WorkflowExecution`；
- 保留统一 `schedule_slot_key = WorkflowExecution.idempotency_key`；
- 新增 `0029_workflow_worker_lease`；
- 新增 `WorkflowWorker` 领域模块；
- 新增 `run_worker.py` 与 `app.entrypoints.worker`；
- Worker 使用 PostgreSQL `FOR UPDATE SKIP LOCKED` 认领 pending Execution；
- Worker 复用唯一 `WorkflowExecutionService` 和 `WorkflowRuntime`；
- Worker 不实现第二套 Trigger、Scheduler、Runtime、Provider 或权限逻辑；
- `WorkflowExecutionService` 增加 Worker ownership fencing，旧 Worker 失去 lease 后不能继续推进 Execution / Node 状态；
- Worker 将 ownership 失效视为 stale consumer，主动放弃任务而不是把竞争结果记录为普通 Runtime 失败；
- `WorkflowExecutionService.run()` 现在区分 HTTP 手动 Run 与 Worker owner，Worker claim 后 HTTP `/run` 不得进入第二个 Runtime；
- Worker 将 claim 时的 `worker_owner` 传递到 `WorkflowExecutionService.run()`，使 claim ownership 与 Runtime 入口保持同一身份边界；
- Node 状态机继续禁止 `running → running`，重复 Runtime 通过 Execution owner fencing 在进入 Runtime 前被阻断。

## 3. 当前执行链

```text
API Service
   │ create/update Trigger
   ▼
PostgreSQL WorkflowTrigger
   │
   ▼
Scheduler Service
   │ slot / lease / misfire
   ▼
WorkflowExecution(status=pending)
   │
   ├── HTTP /run
   │      ├── worker_owner=None 且未被 claim → 允许
   │      └── 已被 Worker claim → 409，禁止重复 Runtime
   │
   ▼
Worker Service
   │ claim + lease + ownership fence
   ▼
WorkflowExecutionService.run(worker_owner=A)
   │
   ▼
WorkflowRuntime
```

## 4. 数据 Contract

`workflow_executions` 新增：

```text
worker_owner
worker_lease_expires_at
worker_attempt
```

这些字段只承担 Worker ownership，不改变既有 Execution 状态机。

## 5. 设计边界

### Scheduler

允许：

- 查询 Scheduled Trigger；
- schedule 初始化；
- lease；
- slot；
- misfire；
- idempotency；
- 创建 pending Execution。

禁止：

- 直接调用 Workflow Runtime；
- 执行模型、工具、节点；
- 复制 WorkflowExecutionService。

### Worker

允许：

- claim pending Execution；
- Worker lease；
- ownership fencing；
- 并发执行；
- 调用正式 WorkflowExecutionService；
- 向 Runtime 入口传递自己的 owner 身份。

禁止：

- 计算 Scheduled slot；
- 修改 Trigger 调度规则；
- 复制 Runtime；
- 建立第二套 Provider；
- 建立 Worker HTTP API。

### HTTP `/run`

允许：

- 对尚未被 Worker claim 的 pending Execution 启动一次 Runtime；
- 保持原有 `409 只有 pending Execution 可以 Run` Contract。

禁止：

- 抢占已由 Worker claim 的 pending Execution；
- 与 Worker 同时进入同一个 Runtime；
- 通过放宽 Node 状态机掩盖重复执行。

## 6. Legacy Definition 兼容

Scheduler 创建的历史兼容 Execution 保留 `scheduled_slot` 元数据。Worker 仅对包含该字段的 Scheduled Execution 启用现有 `allow_legacy_empty_nodes=True` 受控兼容。

普通 Manual Execution 仍然走严格 Workflow Definition 校验。

## 7. 当前风险边界

Worker lease 现在同时承担两层职责：

1. `pending → Worker claim` 的消费 ownership；
2. Runtime 每次 Execution / Node 状态转换时的 ownership fencing。

如果 Runtime 已进入 `running` 后 Worker 进程崩溃，本阶段仍不新增自动 resume；这是后续 Runtime durable execution / checkpoint 任务，而不是通过 Worker 伪造恢复逻辑解决。

## 8. 测试顺序

```text
① Worker ownership fencing Unit
② Worker Unit
③ Backend Regression
④ Alembic upgrade head
⑤ Tenant Safe Real API
⑥ Scheduler/Worker Real Acceptance
⑦ Frontend Regression（受 API Contract 影响时）
⑧ Browser E2E（受 Trigger 行为影响时）
```

本阶段实际结果只能在开发者执行后填写。
