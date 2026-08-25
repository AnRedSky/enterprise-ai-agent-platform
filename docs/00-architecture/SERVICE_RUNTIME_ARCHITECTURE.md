# API / Scheduler / Worker 服务化运行架构

> 评估日期：2026-08-25  
> 当前实施范围：API Service、Scheduler Service 进程解耦；Worker Service 作为后续扩展角色保留，不提前伪造队列或执行实现。

## 1. 架构决策

当前项目已经具备将 API 与 Scheduler 拆成独立进程的条件，而且本次直接完成第一阶段物理拆分：

```text
                         ┌──────────────────────┐
                         │      API Service      │
                         │ FastAPI / HTTP / Auth │
                         └──────────┬───────────┘
                                    │
                         PostgreSQL / Redis / Domain
                                    │
                         ┌──────────▼───────────┐
                         │  Scheduler Service   │
                         │ slot / lease /       │
                         │ misfire / dispatch   │
                         └──────────┬───────────┘
                                    │
                         WorkflowTriggerService
                                    │
                         ┌──────────▼───────────┐
                         │  Workflow Runtime    │
                         │ Execution / Agent    │
                         └──────────────────────┘

后续扩展：
                         ┌──────────────────────┐
                         │    Worker Service    │
                         │ queue / async jobs   │
                         └──────────────────────┘
```

核心原则：

1. API Service 不创建 Scheduler 后台任务；
2. Scheduler Service 不注册 FastAPI Router；
3. Scheduler 仍然复用唯一的 `ScheduledTriggerScheduler`、Repository、Trigger Service 与 Workflow Runtime，不产生第二套调度实现；
4. API 与 Scheduler 可以独立扩缩容、独立重启、独立资源限制；
5. Worker Service 暂不实现，必须等异步任务 Contract、队列基础设施、租约与失败恢复语义明确后再建立正式领域模块。

## 2. 为什么现在拆分

此前 API `lifespan` 同时承担 HTTP 生命周期与 Scheduler 生命周期。该设计在单实例开发阶段可工作，但进入多实例部署后会产生结构性问题：

- 每个 API 实例都会创建一个 Scheduler；
- API 横向扩容会同步扩大 Scheduler 轮询进程数量；
- API 发布、滚动重启与 Scheduler 调度恢复被绑定；
- API CPU / memory 限制与 Scheduler 调度延迟互相影响；
- Scheduler Restart Acceptance 难以区分 API 重启与 Scheduler 重启；
- 后续引入 Worker 时缺少明确的进程角色边界。

虽然当前 PostgreSQL lease / slot 能够保证多实例 ownership 与幂等，但“可以竞争”不等于“应该把 Scheduler 生命周期绑定到 API”。本次拆分解决的是进程职责与部署拓扑，而不是重写现有 Scheduler Contract。

## 3. 目录与入口

```text
backend/
├── app/
│   ├── entrypoints/
│   │   ├── __init__.py
│   │   └── scheduler.py       # Scheduler Service 进程编排
│   ├── api/                   # API Service HTTP 适配
│   ├── services/
│   │   └── workflow_scheduler/ # Scheduler 领域实现
│   └── main.py                # API FastAPI App，不启动 Scheduler
├── run.py                     # API Service 启动入口
└── run_scheduler.py           # Scheduler Service 启动入口
```

`Scheduler` 不直接挂在 `app/` 根目录下，也不把领域代码移动到进程入口。`app/entrypoints` 只负责进程生命周期编排；真正的调度业务继续位于 `services/workflow_scheduler/`，符合 Backend 模块架构中“Service 负责领域规则、Runtime 负责执行编排、入口只负责进程启动”的边界。

## 4. 启动方式

### API Service

```powershell
cd backend
uv run python run.py
```

等价入口：

```powershell
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

API `/health` 返回 `service=api`。

### Scheduler Service

```powershell
cd backend
uv run python run_scheduler.py
```

Scheduler Service 不提供 HTTP API。其健康状态应通过后续独立的 process/metrics/lease observability 机制暴露，不在本次拆分中向 Scheduler 复制一套 HTTP 服务。

## 5. 配置边界

当前 `scheduler_enabled` 保留为 Scheduler Service 的启动开关：

```text
API Service
    └── 不读取该开关来创建 Scheduler

Scheduler Service
    └── scheduler_enabled=true → 启动
    └── scheduler_enabled=false → 明确拒绝启动
```

这样可以避免出现“API 偶然关闭 Scheduler 后，系统悄悄回退到 API 内嵌 Scheduler”的双模式。

## 6. Worker Service 后续扩展原则

Worker 不应简单复制 `ScheduledTriggerScheduler`。它应在出现明确的异步执行队列需求后建立：

```text
API Service
    ↓
Task / Execution Contract
    ↓
Queue / Broker
    ↓
Worker Service
    ↓
Workflow / Agent Runtime
```

Worker 正式实施前必须先确定：

- Task Contract 与版本；
- queue / broker 技术选型；
- task lease / visibility timeout；
- retry / backoff / dead-letter；
- execution idempotency；
- tenant boundary；
- concurrency / rate limit；
- cancellation；
- Audit / Trace；
- graceful shutdown 与 in-flight task recovery。

在这些 Contract 未确定前，禁止创建 `worker.py` 空壳或第二套执行 Runtime。

## 7. 部署拓扑演进

### 当前阶段

```text
API Service × N
Scheduler Service × 1..N
PostgreSQL
Redis
```

Scheduler 可以多实例运行，因为现有 PostgreSQL lease + slot 已经定义了 ownership 与幂等边界。生产环境建议从 1 个 Scheduler 实例开始，在监控与压力验证完成后再扩展。

### 后续 Worker 阶段

```text
API Service × N
Scheduler Service × N
Worker Service × N
PostgreSQL
Redis / Queue Broker
```

三类服务应拥有独立 deployment / process / resource limit / restart policy，但共享稳定 Domain Contract 与 Infrastructure。

## 8. 不做的事情

本次服务化不包含：

- MQ/Kafka/Temporal 引入；
- Workflow Runtime 重写；
- Scheduler Repository 重写；
- 新增第二套 slot/idempotency key；
- 把 Scheduler 领域代码移动到 `app/` 根目录；
- 为未来 Worker 创建无业务实现的空服务；
- 修改既有 API Path、HTTP Contract、tenant isolation、数据库模型或 Scheduler Contract。

## 9. 验收标准

本次拆分必须至少满足：

1. `app.main` 导入不会创建 Scheduler；
2. API `/health` 明确标记 `service=api`；
3. `run.py` 只启动 API；
4. `run_scheduler.py` 只启动 Scheduler；
5. Scheduler Service 复用唯一 `ScheduledTriggerScheduler`；
6. `scheduler_enabled=false` 时 Scheduler 明确拒绝启动；
7. 既有 Backend regression、Real API、Scheduler restart acceptance 继续作为独立 Gate；
8. API Service 与 Scheduler Service 可以分别停止和重启，不需要修改业务代码；
9. 不产生旧入口兼容垫片或第二套 Scheduler 实现。

## 10. 后续实施顺序

```text
本次：API / Scheduler 物理进程解耦
    ↓
补充 Scheduler process observability
    ↓
Scheduler 多实例压力 / lease acceptance
    ↓
明确异步 Task Contract
    ↓
引入 Queue / Broker
    ↓
Worker Service
    ↓
Worker retry / lease / DLQ / cancellation acceptance
```
