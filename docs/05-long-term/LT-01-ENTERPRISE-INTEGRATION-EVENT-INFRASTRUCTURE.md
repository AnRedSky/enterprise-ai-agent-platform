# LT-01 Enterprise Integration / Event Infrastructure

## 1. 目标
建立可靠、可治理、可观测的企业系统集成与事件基础设施，使 Agent、Workflow、Scheduler、Delegation 能与外部业务系统形成稳定异步协作。

## 2. 当前状态
**Phase 2.9 开发中。** Event Contract、Durable Event Persistence、Reliable Delivery 已形成连续实现链路；下一切片进入 Webhook Integration。

## 3. 已完成
- 统一 IntegrationEvent Contract；
- PostgreSQL Durable Event Fact 与幂等唯一约束；
- `FOR UPDATE SKIP LOCKED` 原子 Claim；
- Worker lease、过期恢复、fencing；
- capped exponential retry 与 dead-letter；
- 真实 PostgreSQL 并发/恢复/租户隔离验收；
- Webhook HTTP Provider 第一实现切片：事件 JSON envelope、事件身份头、幂等头、HMAC-SHA256 签名和非 2xx 失败透传。

## 4. 当前缺口
- Webhook destination/subscription 的持久化模型与租户治理；
- destination Secret 的安全存储与轮换；
- Durable Event 到多个 Webhook destination 的正式编排入口；
- delivery audit、回放、查询与运营接口；
- SSRF / 网络出口策略与 endpoint allowlist；
- Workflow/Agent/Scheduler 业务事实接入统一 Event Contract；
- 大规模多 destination 顺序、并发与限流策略。

## 5. 长期拆解
1. 盘点现有 Event/Webhook/Trigger/Audit/Trace/Outbox 实现；
2. 定义业务事件模型与 Integration Contract；
3. 定义可靠投递、幂等、顺序和失败语义；
4. 决策数据库 Outbox、消息队列或其他实现边界；
5. 实现统一 Integration Domain；
6. 接入 Webhook destination/subscription；
7. 接入 Workflow/Agent/Scheduler；
8. 建立 Real API 与故障恢复验收。

## 6. 当前完成判定
2.9-C 已完成真实 PostgreSQL Gate。2.9-D 仅完成 Provider 基础切片，不能视为完整 Webhook Integration 完成；必须继续完成 destination 持久化、可靠投递编排、安全策略、审计/回放及 Real API 验收。

## 7. 明确不做
在 Contract 与 Durable Delivery 边界稳定前不得直接引入 Kafka、MQ、Event Bus 或第二套 Outbox；不得复制现有 Webhook/Trigger/Trace 能力。Webhook Trigger（入站）与 Webhook Provider（出站）保持职责分离。
