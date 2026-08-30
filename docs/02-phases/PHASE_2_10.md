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

- `GET /api/v1/runtime/operations/overview`。
- 统计窗口支持 1 / 24 / 168 小时。
- 返回事件状态、Delivery 状态、重试、死信、成功率、99% SLO、错误预算和 P95 延迟。
- 前端 `/runtime/operations` 提供 Event / Delivery / SLO / Dead Letter 聚合视图。

## 2.10-F Metrics / SLO
状态：**增强切片已实现**。

- `GET /api/v1/runtime/operations/dimensions`；
- 按 Event Type + Destination 聚合 Delivery Durable Facts；
- 当前 Webhook HTTP Provider 作为 canonical provider dimension `webhook_http`；
- `GET /api/v1/runtime/operations/alerts` 提供确定性 SLO / Retry / Dead Letter 告警评估；
- 指标仍全部从 PostgreSQL Durable Event / Delivery facts 实时计算，不建立平行业务事实源。

## 2.10-G Dead Letter Management
状态：**增强切片已实现**。

- tenant-scoped Dead Letter 查询与分页；
- 单条 Replay 与最多 100 项批量 Replay；
- 重复 ID 自动去重；
- 每项独立处理并返回成功/拒绝结果；
- Replay 只重新入队，不同步执行网络请求；
- 每次成功 Replay 通过 canonical Repository 产生不可变 Audit Fact。

## 2.10-H Runtime Operational Acceptance
状态：**Acceptance Gate 已实现，按本地实际执行结果收口**。

必须验证 tenant isolation、Overview / Dimension / SLO / Alert、Dead Letter Replay / Audit，以及 Worker 后续网络投递边界；Gate 不启动或停止 API、Worker、Scheduler、Redis、PostgreSQL，测试数据自动生成和清理。

## 2.10-I Provider / Metrics / Alert / Export / Audit
状态：**开发中，三维时间序列采样、Scheduler 周期评估与通知路由编排切片已完成**。

### I-1 时间序列 Metrics

新增持久化 `runtime_metric_samples`，时间序列样本按 `tenant_id + metric_name + recorded_at` 索引；样本由既有 Durable Event / Delivery facts 聚合生成，不形成第二套业务事实源。

- `POST /api/v1/runtime/operations/metrics/snapshot` 固化当前指标快照；
- `GET /api/v1/runtime/operations/metrics/series` 查询租户隔离的时间序列；
- canonical 全局指标包括 Delivery Success Percent、Retry Count、Dead Letter Count、P95 Delivery Latency；
- 三维样本额外使用 Provider / Destination / Event Type 规范维度。

### I-2 Provider Registry

新增 `runtime_provider_registry`，提供 tenant-scoped Provider 元数据注册。

- `GET/POST /api/v1/runtime/operations/providers`；
- Provider 类型、名称、启用状态、健康状态和非敏感配置可持久化；
- `POST /api/v1/runtime/operations/providers/{provider_id}/health` 对显式 HTTPS healthcheck endpoint 执行受控健康探测；
- 健康探测禁止跟随重定向，并复用统一 SSRF / 出口安全策略；
- Provider 可声明最多 50 项 `capabilities`，用于运维发现，不复制 Provider 实现；
- 禁止保存 `api_key/token/password/secret` 等明文凭据，且敏感字段检查递归覆盖嵌套对象/数组；
- Secret 继续由现有 Secret Resolver 体系管理。

### I-3 Destination Registry

既有 `WebhookDestination` 正式作为 Destination Registry 来源，通过 `GET /api/v1/runtime/operations/destinations` 提供运维视图；不再新增平行 Destination 表。

### I-4 Alert Rule Management

新增 `runtime_alert_rules`，支持 tenant-scoped 的指标、比较符、阈值、窗口和严重级别配置。

- `GET/POST /api/v1/runtime/operations/alert-rules`；
- 当前支持 `> >= < <= ==`；
- 规则仅保存配置，告警评估继续基于可重算 Durable facts；
- 生命周期评估只记录真正的 firing / recovery 状态转换，重复 firing 不重复生成通知事实；
- firing/recovery 已统一发布为 `runtime.alert.firing` / `runtime.alert.recovery` Integration Event，通知层继续通过现有 Delivery 路径消费；
- 所有生命周期转换进入通用 Runtime Operational Audit。

### I-5 Prometheus / OpenTelemetry Export

新增：

- `GET /api/v1/runtime/operations/metrics/prometheus`：输出 Prometheus text exposition；
- `GET /api/v1/runtime/operations/metrics/otlp`：输出 OTLP HTTP 指标结构；
- 导出数据 tenant-scoped，且直接从 Durable facts 计算，避免导出缓存与业务事实漂移。

当前实现不强制引入第三方 SDK，先稳定协议边界；后续接入 OpenTelemetry SDK 时保持现有导出 Contract 不变。

### I-6 Operational Audit

新增 `runtime_operation_audits` 通用运维审计事实，并提供：

- `GET /api/v1/runtime/operations/audit`；
- Provider 注册、Provider 健康探测、Alert Rule 管理及告警生命周期均记录 actor / action / resource / outcome；
- Audit 与 Replay Audit 保持职责分离：Replay 继续使用 Webhook Delivery Audit，通用运维动作使用 Runtime Operational Audit。

### I-7 三维时间序列采样

状态：**第一切片已实现**。

- `RuntimeDimensionSampler` 从 Durable Event + Webhook Delivery facts 直接聚合 Provider / Destination / Event Type 三维样本；
- canonical Provider 固定为 `webhook_http`，Destination 使用稳定 UUID，Event Type 使用 Durable Event 原值；
- 快照接口同时写入全局指标与三维指标样本；
- 时间序列查询支持 `provider`、`destination_id`、`event_type` 三个规范维度过滤；
- 不新增业务事实表，不复制 Delivery 状态机。

### I-8 Scheduler Runtime Alert Evaluation

状态：**第一切片已实现**。

- `RuntimeAlertScheduler` 作为独立 Scheduler Service 周期任务运行；
- 自动发现启用告警规则涉及的 tenant，并为每个 tenant 使用独立数据库 Session；
- 每轮先从 Durable facts 生成指标样本，再调用现有 `RuntimeAlertEvaluator`；
- firing / recovery 仍由 Evaluator 去重、审计并发布 Integration Event；
- Scheduler 不直接执行通知网络请求，避免绕过现有 Delivery Worker。

### I-9 Notification Routing Runtime

状态：**第一切片已实现**。

- `RuntimeNotificationScheduler` 接入独立 Scheduler Service；
- 自动发现存在 pending Durable Integration Event 的 tenant；
- 每个 tenant 使用独立数据库 Session，调用既有 `NotificationDispatcher` 物化 Delivery Facts；
- Routing 仍严格执行 tenant + event type + destination enabled + subscription filter 匹配；
- Scheduler 只负责事件路由编排，不执行外部 HTTP，不修改 Integration Event 状态机；
- Webhook Delivery Worker 继续负责 lease、网络发送、retry、dead-letter 和最终 Delivery Audit。

### I-10 Worker Lifecycle Regression

状态：**单元测试修复完成，等待本地回归结果**。

- 修复 Worker 入口生命周期测试中对 `WebhookDeliveryWorker.DEFAULT_CONCURRENCY` 类级契约的 Mock 缺失；
- 测试显式保留生产构造器需要的类级默认值，并验证 sender / concurrency / lease / max_attempts 参数；
- 错误记录：`docs/04-errors/2026-08-30-worker-entrypoint-test-mock-class-attribute.md`；
- Runtime Real Gate 继续禁止自动启动服务，仅检查 Scheduler / Worker 是否已经由开发者启动；测试身份与业务数据自动生成，不要求人工填写。

## 2.10-I 下一切片

1. 本地执行 Worker 生命周期单元回归与 Backend default regression；
2. 执行 Runtime Notification Lifecycle Real Gate，验证真实 PostgreSQL / Scheduler / Worker 闭环；
3. 完成 fallback exhausted → Notification DLQ 的真实失败链路验收；
4. 完成 Alert → Notification → Provider → Destination Metrics 的维度聚合核验；
5. 完成 Prometheus canonical metric naming / label governance；
6. 接入 OpenTelemetry SDK 的标准 Meter / Resource / tenant-safe attributes；
7. 完成 2.10-I Runtime Acceptance：registry + health + series + scheduler + lifecycle + notification routing + exports + audit + tenant isolation。

## 约束
- Operations API 不绕过 Repository 直接修改 Delivery 状态。
- 所有运维能力必须 tenant-scoped。
- Metrics 不建立平行业务事实源。
- Provider Registry 不保存明文 Secret，不复制 Provider 实现。
- Destination Registry 复用既有 WebhookDestination。
- Export 不改变业务事实，也不得绕过 tenant boundary。
- Operational Audit 必须不可变、可追溯，并记录 actor / action / resource / outcome。
- Provider healthcheck 必须经过统一 SSRF/出口安全校验，不得使用未经约束的用户输入发起内网探测。
- Scheduler Alert Evaluation 不直接执行通知网络请求，只负责指标采样、规则评估与 Integration Event 产生。
- Scheduler Notification Routing 不直接执行通知网络请求，只负责 Durable Event → Delivery Fact 编排；实际网络投递必须由 Delivery Worker 完成。
- 测试 Gate 可以自动探测服务、生成测试上下文并清理测试数据，但禁止自动创建、启动、重启或停止 API、Worker、Scheduler、PostgreSQL、Redis 等服务进程。
