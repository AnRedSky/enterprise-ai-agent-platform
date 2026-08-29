# Phase 2.9 Enterprise Integration / Event Infrastructure

## 1. 阶段目标
在 Phase 2.8 Runtime Integration 收口后，建立 Enterprise Integration / Event Infrastructure：冻结统一事件 Contract，建立 PostgreSQL Durable Event Fact，再实现可靠投递、Webhook Integration 和 Runtime Integration。Redis、Kafka、MQ 均不是 Durable Event Fact 的必要依赖。

## 2. 当前基线
- Phase 2.8 Multi-Agent Collaboration / Runtime Integration：已完成并通过本地 B6 Real Gate。
- Phase 2.9-A Event Contract：已实现。
- Phase 2.9-B Durable Event Persistence：已实现第一切片，数据库 Migration 已验收。
- Phase 2.9-C Reliable Delivery：**第二切片已通过本地真实 PostgreSQL Gate**。
- 当前任务：**2.9-D Webhook Integration：Destination / Subscription / Fan-out Delivery Fact → Reliable Worker / Security Gate**。

## 3. 2.9-A Event Contract

状态：**已实现**。统一事件信封包含 `event_id`、`tenant_id`、`event_type`、`schema_version`、`source`、`subject`、`idempotency_key`、`occurred_at`、`request_id`、`trace_id`、`payload`、`metadata`。

幂等作用域冻结为：

```text
tenant_id + source + event_type + idempotency_key
```

## 4. 2.9-B Durable Event Persistence

状态：**已实现第一切片；数据库 Migration 已验收**。

实现 Durable Event Fact、Repository、0040 Migration、attempt/retry/delivery 字段、幂等唯一约束和稳定 pending 查询。

## 5. 2.9-C Reliable Delivery

状态：**已完成真实 PostgreSQL 验收**。

当前实现：
- PostgreSQL `FOR UPDATE SKIP LOCKED` 原子 Claim；
- `lease_owner` / `lease_expires_at` Worker 租约；
- 过期 running 事件恢复领取；
- attempt count；
- delivered terminal state；
- capped exponential backoff；
- dead-letter；
- tenant isolation；
- lease fencing；
- 外部 Sender 依赖注入；
- Real Gate 自动生成/清理测试租户、事件和幂等数据，不要求手工输入；
- Gate 不启动、不停止 API、Worker、Scheduler、Redis 或 PostgreSQL。

### 本地验收证据
开发者最新反馈：

```text
Phase 2.9-C PostgreSQL concurrency/recovery tests → 5 passed
Targeted delivery unit regression → 15 passed
[PASS] Phase 2.9-C Reliable Delivery PostgreSQL Real Gate completed.
```

此前 Gate marker 过滤、PowerShell 路径和 `.env.example` 基线问题均已修复。

## 6. 2.9-D Webhook Integration

### 6.1 Provider 第一切片
已完成统一 Event → HTTP Webhook Provider：稳定 JSON envelope、事件身份头、幂等头、HMAC-SHA256 签名、HTTPX Client 注入和非 2xx 失败透传。

入站 `WebhookTriggerService` 与出站 `WebhookProvider` 保持严格职责分离。

### 6.2 Destination / Subscription / Delivery Fact
**已实现第一持久化切片。**

新增：
- `webhook_destinations`：tenant-scoped endpoint、Secret 引用、启停状态；
- `webhook_subscriptions`：Event Type → Destination 映射、启停状态、priority；
- `webhook_deliveries`：每个 Event × Destination 独立投递事实；
- Migration `0042_webhook_delivery_facts`；
- `WebhookIntegrationService`：Destination / Subscription 管理与 tenant-scoped Fan-out 规划；
- PostgreSQL 唯一约束 + `ON CONFLICT DO NOTHING`，保证重复规划幂等；
- ORM Registry 已纳入新增模型。

本轮修复了一个运行时完整性缺陷：ORM Registry 已先行引用 Webhook 模型，但模型文件未进入主分支，导致 API/Worker 导入阶段直接触发 `ModuleNotFoundError`。现已补齐 `WebhookDestination`、`WebhookSubscription`、`WebhookDelivery` 模型，并使表名、Destination 关联和 Migration revision 与本阶段 Fan-out 契约一致，同时增加模型注册回归测试。

### 6.3 Management API / Fan-out Planning
**已开始实现下一切片。**

已增加：
- `GET/POST /api/v1/webhooks/destinations`；
- `GET/POST /api/v1/webhooks/subscriptions`；
- `POST /api/v1/webhooks/events/{event_id}/fanout`；
- tenant-scoped `WebhookIntegrationService`；
- Event Type → enabled Destination 的稳定 priority fan-out；
- PostgreSQL 唯一约束驱动的重复规划幂等。

该 API 只负责配置管理和 Delivery Fact 规划，不直接执行 HTTP 投递。

### 下一实现切片
1. Delivery Worker 按 Destination 独立 Claim / lease / retry / dead-letter；
2. Secret Resolver 抽象与运行时 Secret 获取；
3. delivery audit / replay / 查询；
4. endpoint allowlist / SSRF 与网络出口策略；
5. Real HTTP + PostgreSQL Webhook Acceptance Gate；
6. 再将 Webhook Delivery Worker 接入现有 Worker Runtime，而不是新建独立重复调度体系。

## 7. 2.9-E Runtime Integration

待 2.9-D 完成核心 destination 与可靠投递闭环后，将 Workflow / Agent / Scheduler 关键业务事实接入统一 Event Contract，同时保持既有 Runtime 状态机和 Execution Fact 语义。

## 8. 开发边界
- 不把 Redis、Kafka、MQ 作为 Durable Event Fact；
- 不复制已有 Webhook / Trigger / Audit / Trace 实现；
- 不修改已通过 Phase 2.8 B6 Gate 的 Delegation Runtime 主路径；
- 不用 GitHub Actions 结果替代本地验收事实；
- 涉及数据库必须先 Migration，再 Backend/Repository，再测试和 Real API；
- Real Gate 不自动启动或停止 API、Worker、Scheduler、Redis 或 PostgreSQL；依赖服务由开发者按项目环境预先提供；
- 测试数据由脚本自动生成，不要求开发者手工填写租户、Event ID、幂等键或其他测试信息。
