# Phase 2.9 Enterprise Integration / Event Infrastructure

## 1. 阶段目标

在 Phase 2.8 Runtime Integration 收口后，建立 Enterprise Integration / Event Infrastructure 的第一个正式实现切片：先冻结统一事件 Contract，再逐步实现持久化、可靠投递和外部 Integration。不得在 Contract 未稳定前直接引入 Kafka、MQ 或第二套 Outbox。

## 2. 当前基线

- Phase 2.8 Multi-Agent Collaboration / Runtime Integration：已完成并通过本地 B6 Real Gate。
- LT-01：由长期待立项转入 Phase 2.9 正式开发。
- 现有能力：Webhook / Trigger、Audit、Trace、Workflow / Agent / Scheduler Runtime 已存在，但尚未形成统一企业事件领域。

## 3. 本阶段任务

### 2.9-A Event Contract

状态：**已实现第一切片**。

统一事件信封包含：

- `event_id`：全局事件标识；
- `tenant_id`：租户边界；
- `event_type`：稳定事件类型；
- `schema_version`：事件载荷版本；
- `source`：事件生产领域；
- `subject`：事件作用对象；
- `idempotency_key`：生产幂等键；
- `occurred_at`：带时区的业务发生时间；
- `request_id` / `trace_id`：请求与追踪关联；
- `payload` / `metadata`：业务载荷与非业务扩展元数据。

幂等唯一性作用域冻结为：

```text
tenant_id + source + event_type + idempotency_key
```

这一阶段只定义领域契约，不承诺数据库唯一索引或具体消息系统实现；数据库实现将在可靠性语义进一步冻结后进入 Migration。

实现位置：

```text
backend/app/services/integration/
├── __init__.py
└── contract.py
```

### 2.9-B Durable Event Persistence

状态：待实现。

目标：在 2.9-A Contract 基础上实现 PostgreSQL 持久化事实，至少覆盖状态、投递次数、最后错误、下一次投递时间、租户隔离和幂等唯一约束。

进入条件：冻结事件状态机、投递状态和事务边界后建立 Alembic Migration。

### 2.9-C Reliable Delivery

状态：待实现。

目标：实现有限重试、指数退避、失败恢复和死信语义，并明确与 Scheduler / Worker 的职责边界。

### 2.9-D Webhook Integration

状态：待实现。

目标：在现有 Webhook Trigger 基础上统一 endpoint 身份、签名、事件版本、幂等、回放和 delivery audit，不复制现有 Trigger Service。

### 2.9-E Runtime Integration

状态：待实现。

目标：将 Workflow / Agent / Scheduler 的关键业务事实接入统一事件 Contract，同时保留既有 Runtime 状态机与执行语义。

## 4. 第一切片完成证据

本提交新增：

- `backend/app/services/integration/contract.py`
- `backend/app/services/integration/__init__.py`
- `backend/tests/unit/test_integration_event_contract.py`

测试覆盖事件身份、幂等作用域、事件类型约束、时区约束和版本约束。

## 5. 开发顺序

```text
2.9-A Event Contract
    ↓
2.9-B Durable Event Persistence
    ↓
2.9-C Reliable Delivery
    ↓
2.9-D Webhook Integration
    ↓
2.9-E Runtime Integration
```

任何一步发现 Contract 不足，必须先修正 Contract 与对应测试，再继续后续实现。

## 6. 不在本阶段直接做的事情

- Contract 未冻结前不引入 Kafka / MQ / Event Bus；
- 不复制 Webhook / Trigger / Audit / Trace 的已有业务实现；
- 不修改已通过 Phase 2.8 的 Delegation Claim、Worker dispatch、timeout/cancel 和 shutdown cleanup 路径；
- 不把 GitHub Actions 结果作为开发验收依据。

## 7. 验收要求

每个交付切片必须提供：

1. 对应领域单元测试；
2. 涉及数据库时的 Alembic migration 与 `uv run alembic upgrade head` 实际结果；
3. 涉及 HTTP 时的 API Contract / Real API 测试；
4. 涉及后台生命周期时的 Worker / Scheduler 实际运行证据；
5. Phase / Acceptance / PROJECT_STATUS / LT 文档同步更新；
6. 所有变更直接提交 `main`，不创建功能分支。
