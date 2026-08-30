# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.10 Enterprise Integration Event Operations 开发中**
- 当前任务：**2.10-I Runtime Notification Lifecycle / Provider / Metrics / Alert / Export / Operational Audit**
- 最近完成：**Alert firing/recovery、Notification Policy、grouping/dedup/cooldown、Provider fallback、Worker outcome synchronization 与 Runtime Acceptance Gate 实现切片**

开发严格基于远端 `main`，不创建功能分支。

## 2. 已完成能力
- Phase 2.7 Advanced Workflow 主线生产能力完成；
- Durable Workflow / Resume / Frontier / Scheduler 基础设施完成；
- Phase 2.8 Delegation Contract、Durable Entity、Claim、Worker Bridge、generation fencing、timeout/cancel、Audit/Trace、B6 multi-worker Runtime 已完成并通过本地 Real Gate；
- Phase 2.9-A Event Contract 已实现；
- Phase 2.9-B Durable Event Persistence 已实现；
- Phase 2.9-C Reliable Delivery 已通过真实 PostgreSQL Gate；
- Phase 2.9-D Webhook Provider / Destination / Subscription / Fan-out / Delivery Worker / Security / Audit / Replay 已完成 Real Acceptance；
- Phase 2.9-E Runtime Integration 已完成关键业务事实接入，并通过 Runtime Integration Real Acceptance；
- Phase 2.10-A/B/C/D Event、Delivery、Replay、Audit 运维能力已实现；
- Phase 2.10-E Operations Console 第一切片已实现；
- Phase 2.10-F Metrics / SLO 已增强到 Event Type + Destination + Provider 维度及确定性告警；
- Phase 2.10-G Dead Letter 已增强到批量 Replay；
- Phase 2.10-H Runtime Operational Acceptance Gate 已实现。

## 3. Phase 2.10-I 当前实现

### Provider / Metrics / Alert / Export / Audit 基础
状态：**已实现基础切片，继续进入 Runtime Lifecycle 收口**。

已实现：
- `runtime_metric_samples` 时间序列指标持久化；
- Provider / Destination / Event Type 三维时间序列采样；
- `runtime_provider_registry` tenant-scoped Provider 元数据注册与健康探测；
- `runtime_alert_rules` tenant-scoped 告警规则；
- Runtime Alert Scheduler 周期指标采样与告警评估；
- Alert firing/recovery 生命周期实例、severity、routing key、escalation；
- Notification Policy、grouping、cooldown 与稳定 dedup key；
- Provider ordered routing 与 terminal failure fallback；
- WebhookDeliveryWorker 将 delivered/retrying/failed/dead_letter 回写 Notification Delivery；
- terminal `dead_letter` 才允许 Provider fallback，避免 retry 中提前切换；
- fallback exhausted 保持 Notification `dead_letter`，同时产生 `notification.fallback.exhausted` Audit 与 `notification.dlq` Metric；
- Notification Delivery 使用 PostgreSQL 幂等冲突收敛，避免并发重复记录；
- Alert Notification 专用 routing 不再被通用 Notification Scheduler 绕过 Policy 重复路由；`alert.*` 由 AlertLifecycleService 独占编排；
- Notification-level SLO / Metrics / Operational Audit 已有正式聚合入口；
- Prometheus / OTLP Export；
- Runtime Operational Audit 覆盖 Provider、Alert、Notification Delivery 生命周期。

### Worker 生命周期测试修复
状态：**已修复，等待本地实际回归执行**。

- 修复 `tests/unit/test_worker_entrypoint.py` 对 `WebhookDeliveryWorker.DEFAULT_CONCURRENCY` 类级契约缺失的 Mock；
- 测试替身现在显式保留 `DEFAULT_CONCURRENCY=4`，并验证 Worker 构造参数；
- 根因与修复记录：`docs/04-errors/2026-08-30-worker-entrypoint-test-mock-class-attribute.md`；
- 不修改生产 Worker 默认并发行为，不增加兼容层。

### Runtime Notification Lifecycle Acceptance
状态：**Gate 已实现，等待本地实际执行结果收口**。

真实验收脚本：
`backend/scripts/test/phase-2.10/03_alert_notification_lifecycle_real_gate.ps1`

验证链路：

```text
Alert Evaluation
    ↓
Alert Firing / Recovery
    ↓
Notification Policy
    ↓
Grouping / Dedup / Cooldown
    ↓
Provider Routing
    ↓
WebhookDeliveryWorker
    ↓
Notification Delivery Outcome
    ↓
Fallback / Retry / DLQ
    ↓
SLO / Metrics
    ↓
Operational Audit
```

Gate 只负责服务状态探测、测试上下文自动生成、验收执行与清理，不自动启动或停止 API、Scheduler、Worker、PostgreSQL、Redis 等服务；测试数据由脚本自动创建和清理，不要求手工填写测试信息。

## 4. 2.10-I 下一步

1. 本地执行 Worker 生命周期单元回归与 Backend default regression；
2. 执行 Runtime Notification Lifecycle Real Gate，验证真实 PostgreSQL / Scheduler / Worker 闭环；
3. 完成 fallback exhausted → Notification DLQ 的真实失败链路验收；
4. 完成 Alert → Notification → Provider → Destination Metrics 的维度聚合核验；
5. 完成 Prometheus canonical label governance；
6. 接入 OpenTelemetry SDK 标准 Meter / Resource / tenant-safe attributes；
7. 完成 2.10-I 全链路 Real PostgreSQL Acceptance。

## 5. 长期未完成能力
长期企业化能力独立维护在 `docs/05-long-term/`。
