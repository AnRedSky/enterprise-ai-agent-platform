# Phase 2.10 — Enterprise Integration Event Operations

## 目标
在 Phase 2.9 已形成 Durable Integration Event → Reliable Delivery → Webhook → Replay/Audit 基础能力后，建设面向企业运维的统一事件操作面：查询、投递诊断、Replay、审计、后续指标与死信治理。

## 2.10-A / B
已实现 Integration Event 查询、summary、Delivery 查询，全部强制 tenant scope。

## 2.10-C Retry / Replay Operations
状态：**第一切片已实现**。

- `POST /api/v1/runtime/integration-events/deliveries/{delivery_id}/replay`
- 仅 admin 可执行。
- tenant + delivery 双重隔离。
- 仅允许 `delivered` / `dead_letter` replay；pending/running 返回 409。
- replay 重新进入 `pending`，清理旧 lease、delivery timestamp 与错误状态。
- 通过现有 `WebhookDeliveryRepository.replay()` 写入不可变 `WebhookDeliveryAudit(action=replay)`。
- API 不直接执行网络请求，由 Worker 后续领取。

## 2.10-D Delivery Audit Query
状态：**第一切片已实现**。

- `GET /api/v1/runtime/integration-events/deliveries/{delivery_id}/audits`
- tenant + delivery scope。
- 分页查询 delivered / retry / dead_letter / replay 等不可变事实。

## 后续
- 2.10-E Operations Console
- 2.10-F Observability / Metrics
- 2.10-G Dead Letter Management
- 2.10-H Runtime Operational Acceptance

## 约束
- Operations API 不绕过 Repository 直接修改投递状态。
- 所有运维动作必须 tenant-scoped。
- 查询无副作用。
- Replay 只重新入队，不同步执行网络请求。
- 所有 Replay 必须产生不可变审计事实。
