# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.10 Enterprise Integration Event Operations 开发中**
- 当前任务：**2.10-I Provider / Metrics / Alert / Export / Operational Audit 企业级运维扩展**
- 最近完成：**2.10-I Provider 注册、健康探测、告警生命周期、三维时间序列采样与 Scheduler 周期评估切片**

开发严格基于远端 `main`，不创建功能分支。

## 2. 已完成能力
- Phase 2.7 Advanced Workflow 主线生产能力完成；
- Durable Workflow / Resume / Frontier / Scheduler 基础设施完成；
- Phase 2.8 Delegation Contract、Durable Entity、Claim、Worker Bridge、generation fencing、timeout/cancel、Audit/Trace、B6 multi-worker Runtime 已完成并通过本地 Real Gate；
- Phase 2.9-A Event Contract 已实现；
- Phase 2.9-B Durable Event Persistence 已实现；
- Phase 2.9-C Reliable Delivery 已通过真实 PostgreSQL Gate；
- Phase 2.9-D Webhook Provider / Destination / Subscription / Fan-out / Delivery Worker / Security / Audit / Replay 已完成 Real Acceptance；
- Phase 2.9-E Runtime Integration 已完成 Workflow、Agent Tool、Retrieval、Model Provider、Scheduler 关键业务事实接入，并通过 Runtime Integration Real Acceptance；
- Phase 2.10-A/B/C/D Event、Delivery、Replay、Audit 运维能力已实现；
- Phase 2.10-E Operations Console 第一切片已实现；
- Phase 2.10-F Metrics / SLO 已增强到 Event Type + Destination + Provider 维度及确定性告警；
- Phase 2.10-G Dead Letter 已增强到批量 Replay；
- Phase 2.10-H Runtime Operational Acceptance Gate 已实现。

## 3. Phase 2.10 当前实现

### 2.10-E Operations Console
状态：**第一切片已实现**。

- `/runtime/operations` 企业运维控制台；
- Event / Delivery / SLO / Dead Letter 聚合；
- tenant-scoped 查询与管理员 Replay。

### 2.10-F Metrics / SLO
状态：**增强切片已实现**。

- `/api/v1/runtime/operations/overview`；
- `/api/v1/runtime/operations/dimensions`；
- Event Type + Destination + canonical `webhook_http` Provider 维度；
- Success Rate、Retry、Dead Letter、99% SLO、Error Budget、P95 latency；
- `/api/v1/runtime/operations/alerts` 确定性告警评估。

### 2.10-G Dead Letter Management
状态：**增强切片已实现**。

- tenant-scoped 查询、分页；
- 单条及最多 100 项批量 Replay；
- 每项独立结果；
- Replay Audit 可追溯；
- Replay 只重新入队，由 Worker 实际执行网络投递。

### 2.10-H Runtime Operational Acceptance
状态：**Gate 已实现，按本地实际执行结果收口**。

验证范围：tenant isolation、Overview / Event / Delivery / Audit / Replay / Dead Letter / SLO，以及 Worker 网络投递边界。

### 2.10-I Provider / Metrics / Alert / Export / Audit
状态：**开发中，三维时间序列采样与 Scheduler 周期评估切片已完成**。

已实现：

- `runtime_metric_samples` 时间序列指标持久化；
- `/metrics/snapshot` 与 `/metrics/series`；
- Provider / Destination / Event Type 三维时间序列采样；
- 时间序列支持 `provider`、`destination_id`、`event_type` tenant-scoped 过滤；
- `runtime_provider_registry` tenant-scoped Provider 元数据注册；
- Provider capabilities 声明，最多 50 项；
- Provider Registry 递归敏感字段拦截，禁止明文 Secret；
- `POST /providers/{provider_id}/health` 受控 HTTPS healthcheck；
- healthcheck 禁止跟随重定向并复用 SSRF/出口策略；
- `runtime_alert_rules` tenant-scoped 告警规则；
- Alert evaluator 基于 Runtime Operational Audit 实现 firing/recovery 生命周期去重，并发布统一 Integration Event；
- `RuntimeAlertScheduler` 已接入独立 Scheduler Service，周期执行指标采样与告警评估；
- Prometheus / OTLP Export；
- Runtime Operational Audit 覆盖 Provider 创建、健康探测与 Alert 生命周期。

尚未完成：

- 告警 Integration Event → Notification Routing → Delivery Worker 的真实闭环验收；
- 告警通知稳定幂等键、去重和通知失败审计的完整策略；
- Prometheus canonical label governance；
- OpenTelemetry SDK 标准 Meter / Resource / tenant-safe attributes；
- 2.10-I Runtime Acceptance。

## 4. 2.10 顺序

```text
2.10-A Integration Event Operations Query       ✅
        ↓
2.10-B Delivery Operations Query                ✅
        ↓
2.10-C Retry / Replay Operations                ✅
        ↓
2.10-D Delivery Audit Query                     ✅
        ↓
2.10-E Operations Console                       ✅
        ↓
2.10-F Metrics / SLO                            ✅ 增强切片
        ↓
2.10-G Dead Letter Management                   ✅ 增强切片
        ↓
2.10-H Runtime Operational Acceptance           ✅ Gate 已实现
        ↓
2.10-I Provider / Metrics / Alert / Export      🚧 开发中
        ↓
Dimension Sampling                              ✅
        ↓
Scheduler Alert Evaluation                     ✅
        ↓
Integration Event → Notification Delivery     🚧
        ↓
Prometheus / OTel Governance → Runtime Acceptance
```

## 5. 2.10-I 下一步

1. 将 `runtime.alert.firing/recovery` Integration Event 接入现有 Notification Routing 与 Delivery Destination 规则；
2. 完成告警通知稳定幂等键、去重、失败审计和实际 Worker 投递闭环；
3. 增加 Prometheus canonical metric naming / label governance；
4. 接入 OpenTelemetry SDK 标准 Meter / Resource / tenant-safe attributes；
5. 完成 2.10-I Runtime Acceptance。

## 6. 长期未完成能力
长期企业化能力独立维护在 `docs/05-long-term/`：

| ID | 长期能力 | 状态 |
|---|---|---|
| LT-01 | Enterprise Integration / Event Infrastructure | **Phase 2.10 Operations 开发中** |
| LT-02 | Enterprise IAM / SSO / Identity Federation | 待立项 |
| LT-03 | Enterprise Operations Console | **基础控制台已实现，持续增强** |
| LT-04 | API / Developer Platform | 待立项 |
| LT-05 | Observability / SRE | **Metrics / SLO / Export 正在建设** |
| LT-06 | Security / Secrets / Policy | 持续建设 |
| LT-07 | Agent Evaluation / Quality | 待立项 |
| LT-08 | Cost / Quota / Billing | 待立项 |
| LT-09 | Agent Asset / Marketplace | 候选 |
| LT-10 | Production Deployment / HA / Operations | 待立项 |
