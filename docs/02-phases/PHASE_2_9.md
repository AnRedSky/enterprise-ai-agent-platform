# Phase 2.9 Enterprise Integration / Event Infrastructure

## 1. 阶段目标
在 Phase 2.8 Runtime Integration 收口后，建立 Enterprise Integration / Event Infrastructure：冻结统一事件 Contract，建立 PostgreSQL Durable Event Fact，再实现可靠投递、Webhook Integration 和 Runtime Integration。Redis、Kafka、MQ 均不是 Durable Event Fact 的必要依赖。

## 2. 当前基线
- Phase 2.8 Multi-Agent Collaboration / Runtime Integration：已完成并通过本地 B6 Real Gate。
- Phase 2.9-A Event Contract：已实现。
- Phase 2.9-B Durable Event Persistence：已实现第一切片，数据库 Migration 已验收。
- Phase 2.9-C Reliable Delivery：**第二切片已通过本地真实 PostgreSQL Gate**。
- 当前任务：**2.9-D Webhook Integration 第一实现切片**。

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

状态：**第一实现切片已开始**。

本轮正式增加：

```text
backend/app/infrastructure/providers/webhook.py
backend/tests/unit/test_webhook_provider.py
```

Provider 第一切片能力：
- 接收统一 `IntegrationEvent`；
- 生成稳定 JSON envelope；
- 输出 `X-Event-ID`、`X-Event-Type`、`X-Event-Schema-Version`；
- 输出 `Idempotency-Key`；
- 使用 HMAC-SHA256 对实际发送字节签名；
- 输出 `X-Webhook-Signature: sha256=...`；
- 注入 HTTPX Client，支持连接池复用与测试隔离；
- 非 2xx 响应转换为异常，由上层 Durable Delivery 负责 retry/dead-letter。

**重要架构边界：**现有 `WebhookTriggerService` 是入站 Trigger；新增 `WebhookProvider` 是出站 Integration Provider，两者不得合并，也不得复制 Trigger 生命周期实现。

### 下一实现切片
1. Webhook destination/subscription PostgreSQL 模型；
2. tenant-scoped endpoint、Secret 引用和启停状态；
3. Durable Event → destination 的正式编排；
4. delivery audit / replay / 查询；
5. endpoint allowlist / SSRF 与网络出口策略；
6. Real HTTP + PostgreSQL Webhook Acceptance Gate。

## 7. 2.9-E Runtime Integration

待 2.9-D 完成核心 destination 与可靠投递闭环后，将 Workflow / Agent / Scheduler 关键业务事实接入统一 Event Contract，同时保持既有 Runtime 状态机和 Execution Fact 语义。

## 8. 开发边界
- 不把 Redis、Kafka、MQ 作为 Durable Event Fact；
- 不复制已有 Webhook / Trigger / Audit / Trace 实现；
- 不修改已通过 Phase 2.8 B6 Gate 的 Delegation Runtime 主路径；
- 不用 GitHub Actions 结果替代本地验收事实；
- 涉及数据库必须先 Migration，再 Backend/Repository，再测试和 Real API；
- Real Gate 不自动启动或停止任何服务；依赖服务由开发者按项目环境预先提供；
- 测试数据由脚本自动生成，不要求开发者手工填写租户、Event ID、幂等键或其他测试信息。
