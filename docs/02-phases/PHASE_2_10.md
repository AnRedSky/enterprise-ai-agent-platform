# Phase 2.10 — Enterprise Integration Event Operations

## 目标
在 Phase 2.9 已形成 Durable Integration Event → Reliable Delivery → Webhook → Replay/Audit 基础能力后，建设面向企业运维的统一事件操作面：查询、投递诊断、Replay、审计、指标、SLO 与死信治理。

## 2.10-I 当前进度

Phase 2.10-I 已完成 Runtime Notification Lifecycle、Worker tenant/consumer-group 隔离、Claim Competition、Retry/Lease、Dead Letter Replay、Fallback、SLO/Metrics、Runtime Audit、Integration Event 幂等与 Canonical Metrics Export Contract。

### I-11 Worker tenant / consumer-group / Claim Competition

状态：**已完成真实 PostgreSQL Acceptance**。

- Worker 通过 tenant + consumer group 双重边界 Claim Delivery；
- PostgreSQL `FOR UPDATE SKIP LOCKED` 保证同一 Delivery 的并发 Claim 竞争只允许一个 Worker 获得租约；
- Claim acceptance 自动创建并清理隔离租户与 consumer group 的测试事实；
- Real Gate 已纳入 Claim Competition。

### I-12 Canonical Metrics Export Governance

状态：**已完成**。

- `RuntimeMetricContract` 作为 Prometheus / OTLP 的唯一导出规范入口；
- Prometheus 指标名固定映射，仅使用 `tenant_id` 业务标签；
- OTLP 使用 `service.name`、`service.version`、`tenant.id` Resource 属性；
- NaN / Infinity 被拒绝；Prometheus 标签值执行安全转义；
- 未知指标不会静默进入导出结果；
- OpenTelemetry Resource 属性由 `RuntimeMetricContract.otel_resource()` 单一入口生成，避免 SDK Telemetry 与 OTLP Export Contract 漂移。

### I-13 Enterprise Runtime Acceptance

状态：**已完成代码与 Acceptance Gate**。

覆盖 Provider Registry、Alert Rule、Metric Snapshot/Series、Prometheus、OTLP、Operational Audit 与 tenant isolation；测试数据自动创建和清理，Gate 不启动、重启或停止 API、Worker、Scheduler、PostgreSQL、Redis。

### I-14 OpenTelemetry SDK Meter / Resource

状态：**代码与 targeted Acceptance 已实现，等待开发者本地 Real Gate 完成最终运行确认**。

- 新增 `RuntimeTelemetry`，使用 OpenTelemetry SDK `MeterProvider` / `Resource`；
- SDK 指标名称直接复用 `RuntimeMetricContract.OTLP_NAMES`，禁止产生第二套业务指标命名；
- SDK 入口复用 canonical 数值有限性和未知指标校验；
- Enterprise Acceptance 已从 Durable Runtime SLO facts 生成 canonical metric snapshot，并验证 RuntimeTelemetry 的指标集合与 Contract 一致；
- 测试 Resource 使用 `RuntimeMetricContract.otel_resource()`，避免测试维护第二套 service / tenant 属性定义；
- 未接入网络 Exporter，避免 SDK 观测层绕过现有 Prometheus / OTLP Contract。

### I-15 Fallback Exhaustion Final Chain Acceptance

状态：**代码与 Acceptance 覆盖已完成，等待本地 Scheduler + Worker 同时在线后执行最终 Real Gate**。

验收链路固定为：

```text
Alert Evaluation
  → Firing
  → Notification Policy / Group / Dedup
  → Provider Routing
  → Worker Claim
  → Provider Failure
  → Dead Letter
  → Notification Delivery = dead_letter
  → Fallback Provider Exhausted
  → notification.dlq Durable Metric
  → Notification SLO = 0% / Error Budget = 0%
  → Canonical Runtime Metric Export
  → Operational Audit = notification.fallback.exhausted / failure
```

Acceptance 同时验证：

- 主 Delivery 的 `dead_letter` 状态与 consumer group；
- Notification Delivery 的 `dead_letter` 状态及 Provider；
- `notification.dlq` Metric Sample 与 provider / transition 维度；
- Runtime Operations Notification SLO；
- Prometheus / OTLP canonical metric export 与 tenant boundary；
- `notification.delivery.dead_letter` 与 `notification.fallback.exhausted` Audit 事实；
- foreign tenant 不得读取当前租户 Audit；
- 测试 fixture 使用唯一 Integration Event，避免违反 `uq_webhook_delivery_event_destination` 幂等约束。

## 下一步

1. 在本地同步最新 `main`，执行 `uv lock` / `uv run`，确认 OpenTelemetry 依赖与新增 Acceptance；
2. 执行 Backend Regression 与 Phase 2.10-I Real Gate；
3. Real Gate 的服务依赖只允许状态探测；服务缺失时输出标准启动提示但不得自动启动服务；
4. 只有 Scheduler 与 Worker 均已由开发环境预先启动并且 Real Acceptance 全部通过后，才将 Phase 2.10-I 标记为最终收口完成；
5. 最终收口后进入 Phase 2.10-II 或下一主线任务，不再重复建立平行 Runtime Metrics / Notification Provider 实现。

## 约束
- Operations API 不绕过 Repository 直接修改 Delivery 状态。
- 所有运维能力必须 tenant-scoped。
- Metrics 不建立平行业务事实源。
- Provider Registry 不保存明文 Secret，不复制 Provider 实现。
- Destination Registry 复用既有 WebhookDestination。
- Export 不改变业务事实，也不得绕过 tenant boundary。
- Operational Audit 必须不可变、可追溯，并记录 actor / action / resource / outcome。
- Scheduler Alert Evaluation 不直接执行通知网络请求，只负责指标采样、规则评估与 Integration Event 产生。
- Scheduler Notification Routing 不直接执行通知网络请求，只负责 Durable Event → Delivery Fact 编排；实际网络投递必须由 Delivery Worker 完成。
- 测试 Gate 可以自动探测服务、生成测试上下文并清理测试数据，但禁止自动创建、启动、重启或停止 API、Worker、Scheduler、PostgreSQL、Redis 等服务进程。
