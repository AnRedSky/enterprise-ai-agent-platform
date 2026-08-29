# Phase 2.9 Enterprise Integration / Event Infrastructure

## 1. 阶段目标

在 Phase 2.8 Runtime Integration 收口后，建立 Enterprise Integration / Event Infrastructure：冻结统一事件 Contract，建立 PostgreSQL Durable Event Fact，再实现可靠投递、Webhook Integration 和 Runtime Integration。Redis、Kafka、MQ 均不是 Durable Event Fact 的必要依赖。

## 2. 当前基线

- Phase 2.8 Multi-Agent Collaboration / Runtime Integration：已完成并通过本地 B6 Real Gate。
- Phase 2.9-A Event Contract：已实现。
- Phase 2.9-B Durable Event Persistence：已实现第一切片。
- 当前任务：**2.9-C Reliable Delivery**。

## 3. 2.9-A Event Contract

状态：**已实现**。统一事件信封包含 `event_id`、`tenant_id`、`event_type`、`schema_version`、`source`、`subject`、`idempotency_key`、`occurred_at`、`request_id`、`trace_id`、`payload`、`metadata`。

幂等作用域冻结为：

```text
tenant_id + source + event_type + idempotency_key
```

## 4. 2.9-B Durable Event Persistence

状态：**已实现第一切片，待开发者本地数据库验收**。

实现：

```text
backend/app/models/integration_event.py
backend/app/services/integration/repository.py
backend/alembic/versions/0040_integration_events.py
backend/tests/unit/test_integration_event_persistence.py
```

持久化模型提供 Tenant 隔离、Event Contract 核心字段、`pending` 初始状态、attempt count、retry time、delivery time、错误信息、幂等唯一约束和稳定 pending 查询。

## 5. 2.9-C Reliable Delivery

状态：**实现第一切片，待开发者本地验收**。

本轮新增：

```text
backend/app/services/integration/delivery.py
backend/alembic/versions/0041_integration_event_delivery_lease.py
backend/tests/unit/test_integration_event_delivery.py
```

当前实现：

- PostgreSQL `FOR UPDATE SKIP LOCKED` 原子 Claim；
- `lease_owner` / `lease_expires_at` Worker 租约；
- 过期 running 事件可恢复领取；
- 每次 Claim 增加 `attempt_count`；
- 成功后进入 `delivered`；
- 失败后按有限次数进入 `pending` retry；
- 使用 capped exponential backoff；
- 超过最大尝试次数进入 `dead_letter`；
- 外部 Sender 通过依赖注入提供，当前不绑定 Webhook/MQ Provider；
- PostgreSQL 保持 Durable Event Fact 唯一事实源。

### 验收要求

开发者本地执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_integration_event_contract.py tests/unit/test_integration_event_persistence.py tests/unit/test_integration_event_delivery.py
uv run alembic upgrade head
uv run alembic current
uv run pytest -q
```

Migration 应从 `0040_integration_events` 升级到 `0041_integration_event_delivery_lease`。Real API/并发数据库验收尚待补充，不得仅凭单元测试标记为完成。

## 6. 2.9-D Webhook Integration

下一阶段：在现有 Webhook Trigger 基础上统一 endpoint 身份、签名、版本、幂等、回放和 delivery audit，不复制 Trigger Service。

## 7. 2.9-E Runtime Integration

将 Workflow / Agent / Scheduler 关键业务事实接入统一 Event Contract，同时保持既有 Runtime 状态机和 Execution Fact 语义。

## 8. 开发边界

- 不把 Redis、Kafka、MQ 作为 Durable Event Fact；
- 不复制已有 Webhook / Trigger / Audit / Trace 实现；
- 不修改已通过 Phase 2.8 B6 Gate 的 Delegation Runtime 主路径；
- 不用 GitHub Actions 结果替代本地验收事实；
- 涉及数据库必须先 Migration，再 Backend/Repository，再测试和 Real API。
