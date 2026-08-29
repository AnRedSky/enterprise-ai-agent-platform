# Phase 2.10 — Enterprise Integration Event Operations

## 目标
在 Phase 2.9 已形成 Durable Integration Event → Reliable Delivery → Webhook → Replay/Audit 基础能力后，建设面向企业运维的统一事件操作面：查询、投递诊断、Replay、审计、指标、SLO 与死信治理。

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

## 2.10-E Operations Console
状态：**第一切片已实现**。

- 新增 `GET /api/v1/runtime/operations/overview`。
- 统计窗口支持 1 / 24 / 168 小时，服务端最大限制 168 小时。
- 返回事件状态分布、Delivery 状态分布、重试数量、死信数量。
- 返回投递成功率、99% SLO 目标、剩余错误预算和 P95 投递延迟。
- 新增前端 `/runtime/operations` 企业运维控制台入口。
- 总览提供 Event / Delivery / SLO / Dead Letter 聚合视图。
- 死信支持 tenant-scoped 查询和通过既有 Replay API 重新入队。
- 浏览器不直接调用 Webhook endpoint，Replay 仍由 Worker 异步执行。

## 2.10-F Metrics / SLO
状态：**基础切片已实现，后续继续增强**。

当前指标均从 PostgreSQL Durable Event / Delivery 事实实时聚合，不引入第二套业务事实源。

已提供：
- Event 总量及状态计数；
- Delivery 总量及状态计数；
- 重试数量；
- Dead Letter 数量；
- Delivery Success Rate；
- 99% Delivery SLO；
- Error Budget Remaining；
- P95 Delivery Latency。

后续增强：按事件类型 / Provider / Destination 分维度聚合、时间序列指标、告警规则与 Prometheus/OpenTelemetry 导出。

## 2.10-G Dead Letter Management
状态：**第一切片已实现**。

- tenant-scoped Dead Letter 查询；
- 分页；
- 展示 attempt / HTTP / error / lease / timestamps；
- 管理员可通过 Replay API 重新进入 `pending`；
- Replay 产生不可变审计事实。

后续增强：批量 Replay、筛选、人工关闭/归档、失败原因分类、重试策略诊断。

## 2.10-H Runtime Operational Acceptance
状态：**待执行**。

Acceptance 必须验证：

1. tenant A 无法看到 tenant B 的 Event / Delivery / Audit / Dead Letter；
2. overview 与列表使用相同 tenant scope；
3. SLO 指标来自真实 PostgreSQL Durable facts；
4. Dead Letter Replay 重新进入 Worker 投递链路；
5. Replay Audit 可追溯；
6. Real HTTP + PostgreSQL 链路保持不变；
7. Frontend Operations Console 与 Runtime API Contract 一致。

## 约束
- Operations API 不绕过 Repository 直接修改投递状态。
- 所有运维动作必须 tenant-scoped。
- 查询无副作用。
- Replay 只重新入队，不同步执行网络请求。
- 所有 Replay 必须产生不可变审计事实。
- Metrics 必须从已有 Durable Event / Delivery 事实聚合，不建立平行事实源。
