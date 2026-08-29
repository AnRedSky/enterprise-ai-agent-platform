# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.10 Enterprise Integration Event Operations 开发中**
- 当前任务：**2.10-E Operations Console / 2.10-F Metrics / SLO / 2.10-G Dead Letter Management 基础切片**
- 最近完成：**2.10-C Retry / Replay、2.10-D Delivery Audit、2.10-E Operations Console 第一切片**

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
- Integration Event 已提供 tenant-scoped operations query API；
- Phase 2.9-D/E Real Acceptance 已验证真实 HTTP + PostgreSQL、tenant isolation、Webhook delivery/replay/audit 链路。

## 3. Phase 2.9 收口结论
Phase 2.9-D：**已完成 Real Acceptance**。

Phase 2.9-E：**已完成 Runtime Integration Real Acceptance**。

统一业务事实链路：

```text
Workflow / Agent Tool / Retrieval / Model Provider / Scheduler
        ↓
Durable Integration Event
        ↓
Reliable Delivery / Webhook
        ↓
Replay / Audit
        ↓
Tenant-scoped Operations Query
```

## 4. Phase 2.10 当前实现

### 2.10-A Integration Event Operations Query
状态：**第一切片已实现**。

- `GET /api/v1/runtime/integration-events`；
- 强制当前 JWT `tenant_id`；
- 分页及 event_type / source / status / subject / trace_id / request_id / 时间范围过滤；
- `GET /api/v1/runtime/integration-events/summary`，返回 total、status_counts、source_counts、generated_at。

### 2.10-B Delivery Operations Query
状态：**第一切片已实现**。

- `GET /api/v1/runtime/integration-events/{integration_event_id}/deliveries`；
- tenant + integration_event 双重范围；
- 分页、状态过滤；
- lease、attempt、response、error、delivery timestamps 等运维事实。

### 2.10-C Retry / Replay Operations
状态：**第一切片已实现**。

- `POST /api/v1/runtime/integration-events/deliveries/{delivery_id}/replay`；
- 仅 admin；
- tenant + delivery scope；
- delivered / dead_letter 可 Replay，pending/running 返回 409；
- Replay 后回到 pending，由 Worker 后续领取；
- 写入不可变 Webhook Delivery Audit。

### 2.10-D Delivery Audit Query
状态：**第一切片已实现**。

- `GET /api/v1/runtime/integration-events/deliveries/{delivery_id}/audits`；
- tenant + delivery scope；
- 分页查询 delivered / retry / dead_letter / replay 等不可变事实。

### 2.10-E Operations Console
状态：**第一切片已实现**。

- 前端新增 `/runtime/operations`；
- AppShell 增加“运行运维”入口；
- Event / Delivery / SLO / Dead Letter 聚合视图；
- 死信列表支持管理员重新投递；
- Replay 仍通过后端可靠投递链路执行，不由浏览器直接访问目标 endpoint。

### 2.10-F Metrics / SLO
状态：**基础切片已实现**。

新增 `GET /api/v1/runtime/operations/overview`，从真实 PostgreSQL Durable Event / Delivery facts 聚合：
- Event 总量及状态计数；
- Delivery 总量及状态计数；
- retry count；
- dead letter count；
- Delivery Success Rate；
- 99% Delivery SLO；
- Error Budget Remaining；
- P95 Delivery Latency。

后续继续增强 Provider / Destination / Event Type 维度、时间序列、告警和 Prometheus / OpenTelemetry 导出。

### 2.10-G Dead Letter Management
状态：**第一切片已实现**。

- `GET /api/v1/runtime/operations/dead-letters`；
- tenant-scoped 分页；
- attempt / HTTP / error / lease / timestamps 运维信息；
- 通过现有 Replay API 重新入队；
- Replay Audit 可追溯。

后续继续增加批量 Replay、筛选、归档、失败原因分类与策略诊断。

## 5. Phase 2.10 顺序

```text
2.10-A Integration Event Operations Query       ✅
        ↓
2.10-B Delivery Operations Query                ✅
        ↓
2.10-C Retry / Replay Operations                ✅ 第一切片
        ↓
2.10-D Delivery Audit Query                     ✅ 第一切片
        ↓
2.10-E Operations Console                       ✅ 第一切片
        ↓
2.10-F Metrics / SLO                            ✅ 基础切片
        ↓
2.10-G Dead Letter Management                   ✅ 第一切片
        ↓
2.10-H Runtime Operational Acceptance           ⏳ 下一收口任务
```

## 6. 长期未完成能力
长期企业化能力独立维护在 `docs/05-long-term/`：

| ID | 长期能力 | 状态 |
|---|---|---|
| LT-01 | Enterprise Integration / Event Infrastructure | **Phase 2.10 Operations 开发中** |
| LT-02 | Enterprise IAM / SSO / Identity Federation | 待立项 |
| LT-03 | Enterprise Operations Console | **基础运维控制台已实现，持续增强** |
| LT-04 | API / Developer Platform | 待立项 |
| LT-05 | Observability / SRE | **基础 SLO 指标已实现，持续建设** |
| LT-06 | Security / Secrets / Policy | 持续建设 |
| LT-07 | Agent Evaluation / Quality | 待立项 |
| LT-08 | Cost / Quota / Billing | 待立项 |
| LT-09 | Agent Asset / Marketplace | 候选 |
| LT-10 | Production Deployment / HA / Operations | 待立项 |

所有实现仍遵循 Contract → Migration → Backend → Unit/Integration/Contract → Real API → Acceptance；当前 2.10-E/F/G 基础切片不引入数据库结构变更。