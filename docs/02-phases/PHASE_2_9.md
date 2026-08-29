# Phase 2.9 Enterprise Integration / Event Infrastructure

## 1. 阶段目标

在 Phase 2.8 Runtime Integration 收口后，建立 Enterprise Integration / Event Infrastructure：冻结统一事件 Contract，建立 PostgreSQL Durable Event Fact，再实现可靠投递、Webhook Integration 和 Runtime Integration。Redis、Kafka、MQ 均不是 Durable Event Fact 的必要依赖。

## 2. 当前基线

- Phase 2.8 Multi-Agent Collaboration / Runtime Integration：已完成并通过本地 B6 Real Gate。
- Phase 2.9-A Event Contract：已实现。
- Phase 2.9-B Durable Event Persistence：已实现第一切片，数据库 Migration 已由开发者本地升级至 `0041`。
- Phase 2.9-C Reliable Delivery：已实现第一切片；本地定向测试曾因错误数据库 import 在 collection 阶段失败，现已修复，待开发者重新执行定向测试确认。
- 当前任务：**2.9-C Reliable Delivery 第二切片：真实 PostgreSQL 并发验收**。

## 3. 2.9-A Event Contract

状态：**已实现**。统一事件信封包含 `event_id`、`tenant_id`、`event_type`、`schema_version`、`source`、`subject`、`idempotency_key`、`occurred_at`、`request_id`、`trace_id`、`payload`、`metadata`。

幂等作用域冻结为：

```text
tenant_id + source + event_type + idempotency_key
```

## 4. 2.9-B Durable Event Persistence

状态：**已实现第一切片；本地 Migration 已验收，完整 Regression 仍以开发者最新执行结果为准**。

实现：

```text
backend/app/models/integration_event.py
backend/app/services/integration/repository.py
backend/alembic/versions/0040_integration_events.py
backend/tests/unit/test_integration_event_persistence.py
```

持久化模型提供 Tenant 隔离、Event Contract 核心字段、`pending` 初始状态、attempt count、retry time、delivery time、错误信息、幂等唯一约束和稳定 pending 查询。

## 5. 2.9-C Reliable Delivery

状态：**第一切片已实现；进入第二切片真实并发验收**。

实现：

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
- PostgreSQL 保持 Durable Event Fact 唯一事实源；
- Delivery Service 使用正式数据库基础设施入口 `app.infrastructure.db`，不再引用不存在的旧 `app.core.database` 路径；
- 定向单元测试已增加无事件、成功投递和失败重试编排覆盖。

### 已处理的本地反馈

开发者首次执行 2.9-C 定向测试时，三个测试模块均在 collection 阶段因：

```text
ModuleNotFoundError: No module named 'app.core.database'
```

而失败。根因是 Delivery Service 错误引用不存在的旧数据库模块；现已修正为 `from app.infrastructure.db import SessionLocal`。该错误已单独记录至：

```text
docs/04-errors/2026-08-29-phase-2-9-delivery-database-import.md
```

### 当前第二切片验收目标

必须使用真实 PostgreSQL 验证：

1. 两个或以上 Worker 并发 Claim 时同一 Event 只能被一个租约持有者领取；
2. Worker 在租约内成功投递后只产生一个 `delivered` 事实；
3. Worker 崩溃/租约过期后事件可以被另一 Worker 恢复；
4. Sender 临时失败进入 retry，并按退避时间重新变为可领取状态；
5. 达到最大尝试次数后进入 `dead_letter`；
6. 不同 tenant 之间不能互相 Claim Event；
7. 失去租约的旧 Worker 不能覆盖新 Worker 的最终状态；
8. 整个过程不依赖后台 Scheduler 自动消费测试数据。

### 当前验收命令

```powershell
cd backend
uv run pytest -q tests/unit/test_integration_event_contract.py tests/unit/test_integration_event_persistence.py tests/unit/test_integration_event_delivery.py
uv run alembic upgrade head
uv run alembic current
uv run pytest -q
```

Real API / 真实 PostgreSQL 并发验收应在专用 Gate 中执行；不得仅凭单元测试标记 2.9-C 完成。

## 6. 2.9-D Webhook Integration

下一阶段：在现有 Webhook Trigger 基础上统一 endpoint 身份、签名、版本、幂等、回放和 delivery audit，不复制 Trigger Service。

## 7. 2.9-E Runtime Integration

将 Workflow / Agent / Scheduler 关键业务事实接入统一 Event Contract，同时保持既有 Runtime 状态机和 Execution Fact 语义。

## 8. 开发边界

- 不把 Redis、Kafka、MQ 作为 Durable Event Fact；
- 不复制已有 Webhook / Trigger / Audit / Trace 实现；
- 不修改已通过 Phase 2.8 B6 Gate 的 Delegation Runtime 主路径；
- 不用 GitHub Actions 结果替代本地验收事实；
- 涉及数据库必须先 Migration，再 Backend/Repository，再测试和 Real API；
- Real Gate 不自动启动或停止 Worker、Scheduler、API、PostgreSQL、Redis 等服务；依赖服务必须由开发者按项目环境预先提供，Gate 只负责检查前置条件并执行测试；
- 测试数据由脚本自动生成，不要求开发者手工填写租户、Event ID、幂等键或其他测试信息。
