# API / Scheduler / Worker 服务化运行架构

> 评估日期：2026-08-25  
> 当前实施范围：API Service、Scheduler Service 已独立；本轮进一步完成 Scheduler → Worker 执行解耦，第一版使用 PostgreSQL `WorkflowExecution` 作为持久化 Task Contract。

## 1. 架构决策

当前服务链路固定为：

```text
                         ┌──────────────────────┐
                         │      API Service      │
                         │ FastAPI / HTTP / Auth │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         Workflow / Trigger Domain
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  Scheduler Service   │
                         │ slot / lease /       │
                         │ misfire / dispatch   │
                         └──────────┬───────────┘
                                    │
                          PostgreSQL pending Execution
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │    Worker Service    │
                         │ claim / concurrency  │
                         │ execution lease      │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         WorkflowExecutionService
                                    │
                                    ▼
                         Workflow Runtime / Agent
```

核心原则：

1. API Service 不创建 Scheduler 或 Worker 后台任务；
2. Scheduler Service 不注册 FastAPI Router，也不执行 Workflow Runtime；
3. Worker Service 不计算 Scheduler slot，也不复制 Trigger / Runtime；
4. Scheduler 负责“什么时候产生执行任务”，Worker 负责“执行任务”；
5. WorkflowExecutionService / WorkflowRuntime 仍是唯一正式执行入口；
6. 服务角色由启动入口确定，不使用 `SCHEDULER_ENABLED` / `WORKER_ENABLED` 之类的角色切换开关。

## 2. 当前服务入口

```text
backend/run.py
    → API Service

backend/run_scheduler.py
    → Scheduler Service

backend/run_worker.py
    → Worker Service
```

三个入口均通过 `uv run` 启动，且身份固定。

## 3. Scheduler / Worker Task Contract

第一版不引入新的 MQ/Kafka。PostgreSQL `workflow_executions` 直接承担持久化任务 Contract。

Scheduler 创建：

```text
WorkflowExecution
├── status = pending
├── idempotency_key = scheduled:<trigger_id>:<slot>
├── input_data.scheduled_slot
├── input_data.planned_at
└── input_data.recovery
```

Worker claim：

```text
pending
  ↓ SELECT ... FOR UPDATE SKIP LOCKED
worker_owner = worker:<uuid>
worker_lease_expires_at = now + 60s
worker_attempt += 1
  ↓ commit
WorkflowExecutionService.run()
  ↓
running → node execution → completed / failed
```

Scheduler 与 Worker 不通过进程内对象传递任务，也不共享进程生命周期。

## 4. 为什么第一版使用 PostgreSQL

Phase 2.4 已经把 Scheduler 的 durable state 建立在 PostgreSQL 上，因此继续使用 PostgreSQL 作为第一版 Task Contract 可以避免引入第二套 Broker 基础设施。

当前可以获得：

- Scheduler 重启不丢 pending Execution；
- Worker 多实例可通过 `SKIP LOCKED` 分散消费；
- Execution 与 Audit / Trace 在同一持久化边界内；
- Scheduler slot idempotency 与 Execution idempotency 继续使用同一键空间；
- 后续可以在不改变 Workflow Runtime 的情况下替换 Task 投递层。

## 5. Scheduler 边界

Scheduler Service 负责：

```text
Trigger discovery
    ↓
Schedule persistence
    ↓
Lease ownership
    ↓
Misfire selection
    ↓
Schedule slot claim
    ↓
Create pending WorkflowExecution
    ↓
Bind slot → Execution
    ↓
Advance next_run_at
```

Scheduler Service **不再**调用：

```text
WorkflowExecutionService.run()
WorkflowRuntime.execute()
Model Provider
Tool execution
```

因此一个 Scheduler tick 的耗时不会直接受到 LLM / Tool Runtime 的长任务影响。

## 6. Worker 边界

Worker Service 负责：

```text
Claim pending Execution
    ↓
Load Workflow + WorkflowVersion
    ↓
WorkflowExecutionService.run()
    ↓
WorkflowRuntime
```

Worker 不负责：

- Scheduled slot 计算；
- timezone / DST；
- misfire；
- Trigger config；
- Scheduler lease；
- HTTP API；
- Provider 适配；
- 第二套 Execution 状态机。

## 7. Worker Lease

Migration：`0029_workflow_worker_lease`

字段：

```text
worker_owner
worker_lease_expires_at
worker_attempt
```

claim 条件：

```text
status = pending
AND
(worker_owner IS NULL OR worker_lease_expires_at <= now)
```

数据库使用：

```sql
SELECT ...
FOR UPDATE SKIP LOCKED
LIMIT 1
```

claim 完成后提交事务，再进入 WorkflowExecutionService。这样多个 Worker 可以同时运行而不重复领取同一个 pending Execution。

### 当前恢复边界

Worker lease 当前只覆盖 `pending → claim`。

如果 Worker 在进入 Runtime 前崩溃，lease 到期后 pending Execution 可以再次被认领。

如果 Runtime 已经将 Execution 转为 `running` 后进程崩溃，本阶段不自动恢复 running Execution。该问题需要后续单独建立 Runtime checkpoint / execution lease / resume Contract，不能在 Worker 中复制一套状态机解决。

## 8. Legacy Workflow Definition 兼容

历史 Scheduled Workflow 可能包含可确定语义的空 nodes Definition。现有 Scheduler 路径已经通过 `allow_legacy_empty_nodes=True` 做受控兼容。

Worker 不扩大兼容范围：

```text
scheduled_slot 存在
    → 允许沿用 Scheduler 历史兼容 Contract

普通 Manual Execution
    → 严格 Workflow Definition 校验
```

Worker 通过正式 WorkflowExecutionService 进入 Runtime，不创建第三套 Definition validator。

## 9. Tenant Boundary

Worker 不从 HTTP 请求推断 tenant，也不创建新的权限模型。

任务自身携带：

```text
tenant_id
workflow_id
workflow_version_id
created_by
```

Worker 只加载任务关联的 Workflow / Version，并复用既有 Workflow Execution / Governance / Runtime Contract。

## 10. 幂等

Scheduler slot key：

```text
scheduled:<trigger_id>:<interval_slot>
```

同时作为：

```text
WorkflowScheduleSlot.schedule_slot_key
WorkflowExecution.idempotency_key
```

Worker 不生成新的幂等键，也不重新计算 slot。Scheduler 重复 tick、服务重启、Worker 多实例 claim 都必须收敛到同一 Execution。

## 11. 并发模型

默认 Worker：

```text
poll interval = 1s
concurrency = 4
lease = 60s
```

可以运行多个 Worker Service：

```text
Worker A ─┐
Worker B ─┼─ PostgreSQL SKIP LOCKED → 不同 pending Execution
Worker C ─┘
```

后续可独立增加 priority、per-tenant quota、retry、DLQ、cancellation 与 capability routing，但这些能力不得反向进入 Scheduler 时间计算模块。

## 12. 目录

```text
backend/
├── app/
│   ├── entrypoints/
│   │   ├── scheduler.py
│   │   └── worker.py
│   ├── services/
│   │   ├── workflow_scheduler/
│   │   └── workflow_worker/
│   └── main.py
├── run.py
├── run_scheduler.py
└── run_worker.py
```

领域实现位于 `services/<domain>/`，进程生命周期位于 `entrypoints/`，符合 Backend 模块架构规则。

## 13. 部署拓扑

### 当前

```text
API Service × N
Scheduler Service × 1..N
Worker Service × 1..N
PostgreSQL
Redis
```

三类服务拥有独立 process / resource / restart policy，但共享正式 Domain / Infrastructure Contract。

### 后续 Broker 演进

如果 PostgreSQL polling 成为吞吐瓶颈，可以将：

```text
Scheduler
    ↓
PostgreSQL pending Execution
    ↓
Worker polling
```

替换为：

```text
Scheduler
    ↓
Task Outbox / Broker
    ↓
Worker
```

但必须保持 `WorkflowExecution` 为业务执行状态事实源，避免 MQ message 与业务状态形成不可收敛的双写事实源。

## 14. 不做的事情

本轮不包含：

- Kafka / Celery / Temporal 引入；
- 第二套 Execution Service；
- 第二套 Runtime；
- Worker HTTP API；
- running Execution 自动 resume；
- DLQ；
- Worker 自定义权限模型；
- API / Scheduler 进程边界重新设计。
