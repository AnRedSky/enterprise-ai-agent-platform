# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.10 Enterprise Integration Event Operations 开发中**
- 当前任务：**2.10-I Provider / Metrics / Alert / Export / Operational Audit 企业级运维扩展**
- 最近完成：**2.10-H Runtime Operational Acceptance Gate 实现、2.10-F/G 增强切片**

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

验证范围：tenant isolation、Overview / Dimension / SLO / Alert、Dead Letter Replay / Audit、Worker 网络投递边界。

### 2.10-I Provider / Metrics / Alert / Export / Audit
状态：**开发中**。

已实现第一批企业运维基础设施：

- `runtime_metric_samples` 时间序列指标持久化；
- `/metrics/snapshot` 与 `/metrics/series`；
- `runtime_provider_registry` tenant-scoped Provider 元数据注册；
- `/providers` Provider Registry API；
- 既有 `WebhookDestination` 作为正式 Destination Registry 来源；
- `runtime_alert_rules` tenant-scoped 告警规则；
- `/alert-rules` Alert Rule 管理 API；
- `/metrics/prometheus` Prometheus text export；
- `/metrics/otlp` OTLP HTTP 指标结构导出；
- `runtime_operation_audits` 通用运维审计事实与 `/audit` 查询；
- Provider Registry 禁止保存明文 Secret；Destination 不创建平行注册表；Metrics 不建立平行业务事实源。

## 4. Phase 2.10 顺序

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
Provider health + Alert lifecycle + OTel SDK + Runtime Acceptance
```

## 5. 2.10-I 下一步

1. Provider Registry 接入真实 Provider 健康探测与能力声明；
2. 增加 Provider / Destination / Event Type 时间序列维度采样；
3. Alert Rule 接入 Scheduler 周期评估与通知 Delivery；
4. 增加告警去重、恢复事件、生命周期及通知失败审计；
5. 建立 Prometheus metric naming / label governance；
6. 接入 OpenTelemetry SDK 标准 Meter / Resource / tenant-safe attributes；
7. 完成 2.10-I Runtime Acceptance。

## 6. 长期未完成能力
长期企业化能力独立维护在 `docs/05-long-term/`：

| ID | 长期能力 | 状态 |
|---|---|---|
| LT-01 | Enterprise Integration / Event Infrastructure | **Phase 2.10 Operations 开发中** |
| LT-02 | Enterprise IAM / SSO / Identity Federation | 待立项 |
| LT-03 | Enterprise Operations Console | **基础控制台已实现，持续增强** |
| LT-04 | API / Developer Platform | 待立项 |
| LT-05 | Observability / SRE | **Metrics / SLO 基础与 Export 正在建设** |
| LT-06 | Security / Secrets / Policy | 持续建设 |
| LT-07 | Agent Evaluation / Quality | 待立项 |
| LT-08 | Cost / Quota / Billing | 待立项 |
| LT-09 | Agent Asset / Marketplace | 候选 |
| LT-10 | Production Deployment / HA / Operations | 待立项 |
