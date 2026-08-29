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
状态：**开发中，企业级运维扩展切片已启动**。

### I-1 时间序列 Metrics

新增持久化 `runtime_metric_samples`，时间序列样本按 `tenant_id + metric_name + recorded_at` 索引；样本由既有 Durable Event / Delivery facts 聚合生成，不形成第二套业务事实源。

- `POST /api/v1/runtime/operations/metrics/snapshot` 固化当前指标快照；
- `GET /api/v1/runtime/operations/metrics/series` 查询租户隔离的时间序列；
- 当前 canonical 指标：Delivery Success Percent、Retry Count、Dead Letter Count、P95 Delivery Latency。

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
- 首次 normal 不产生通知转换，避免规则创建后立即产生无意义恢复事件；
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

## 2.10-I 下一切片

1. 增加按 Provider / Destination / Event Type 的时间序列维度采样；
2. 将 Alert Rule 评估接入 Scheduler 周期任务，并把 firing/recovery 转换接入统一 Integration Event Contract；
3. 增加告警通知 Delivery 路由、去重键与通知失败审计；
4. 增加 Prometheus canonical metric naming / label governance；
5. 接入 OpenTelemetry SDK 的标准 Meter / Resource / tenant-safe attributes；
6. 完成 2.10-I Runtime Acceptance：registry + health + series + rules + lifecycle + exports + audit + tenant isolation。

## 约束
- Operations API 不绕过 Repository 直接修改 Delivery 状态。
- 所有运维能力必须 tenant-scoped。
- Metrics 不建立平行业务事实源。
- Provider Registry 不保存明文 Secret，不复制 Provider 实现。
- Destination Registry 复用既有 WebhookDestination。
- Export 不改变业务事实，也不得绕过 tenant boundary。
- Operational Audit 必须不可变、可追溯，并记录 actor / action / resource / outcome。
- Provider healthcheck 必须经过统一 SSRF/出口安全校验，不得使用未经约束的用户输入发起内网探测。
