# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.10 Enterprise Integration Event Operations 开发中**
- 当前任务：**2.10-E Operations Console / Observability 基础能力**
- 最近完成：**2.10-C Retry / Replay Operations、2.10-D Delivery Audit Query 第一切片**

开发严格基于远端 `main`，不创建功能分支。

## 2. 已完成能力
- Phase 2.7 Advanced Workflow 主线生产能力完成；
- Durable Workflow / Resume / Frontier / Scheduler 基础设施完成；
- Phase 2.8 Delegation Contract、Durable Entity、Claim、Worker Bridge、generation fencing、timeout/cancel、Audit/Trace、B6 multi-worker Runtime 已完成并通过本地 Real Gate；
- Worker shutdown AsyncEngine cancellation-safe disposal 已完成；
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

已实现：
- `GET /api/v1/runtime/integration-events`；
- 强制使用当前 JWT `tenant_id`；
- 分页；
- event_type / source / status / subject / trace_id / request_id 过滤；
- occurred_from / occurred_to 时间范围过滤；
- `GET /api/v1/runtime/integration-events/summary`；
- summary 返回 total、status_counts、source_counts、generated_at；
- summary 与列表使用相同 tenant scope 和过滤口径。

### 2.10-B Delivery Operations Query
状态：**第一切片已实现**。

已实现：
- `GET /api/v1/runtime/integration-events/{integration_event_id}/deliveries`；
- 强制 tenant + integration_event 双重范围；
- 支持分页与 Delivery status 过滤；
- 返回 lease、attempt、response、error、delivery timestamps 等运维事实；
- 查询不修改 Delivery 状态。

### 2.10-C Retry / Replay Operations
状态：**第一切片已实现**。

已实现：
- `POST /api/v1/runtime/integration-events/deliveries/{delivery_id}/replay`；
- 仅 admin 可执行；
- 强制 tenant + delivery scope；
- 仅允许 `delivered` / `dead_letter` Delivery replay；pending/running 返回 409；
- replay 后 Delivery 回到 `pending`，清理旧 lease、delivery timestamp 与错误状态；
- 通过既有 Repository 写入不可变 `WebhookDeliveryAudit(action=replay)`；
- API 不直接执行网络请求，由 Delivery Worker 后续领取。

### 2.10-D Delivery Audit Query
状态：**第一切片已实现**。

已实现：
- `GET /api/v1/runtime/integration-events/deliveries/{delivery_id}/audits`；
- 强制 tenant + delivery scope；
- 分页；
- 可查询 delivered / retry / dead_letter / replay 等不可变运维事实。

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
2.10-E Operations Console / Observability       🔄 下一任务
        ↓
2.10-F Metrics / SLO / Alerting                 ⏳
        ↓
2.10-G Dead Letter Management                   ⏳
        ↓
2.10-H Runtime Operational Acceptance           ⏳
```

## 6. 长期未完成能力
长期企业化能力独立维护在 `docs/05-long-term/`：

| ID | 长期能力 | 状态 |
|---|---|---|
| LT-01 | Enterprise Integration / Event Infrastructure | **Phase 2.10 Operations 开发中** |
| LT-02 | Enterprise IAM / SSO / Identity Federation | 待立项 |
| LT-03 | Enterprise Operations Console | 开发中 |
| LT-04 | API / Developer Platform | 待立项 |
| LT-05 | Observability / SRE | 待立项 |
| LT-06 | Security / Secrets / Policy | 持续建设 |
| LT-07 | Agent Evaluation / Quality | 待立项 |
| LT-08 | Cost / Quota / Billing | 待立项 |
| LT-09 | Agent Asset / Marketplace | 候选 |
| LT-10 | Production Deployment / HA / Operations | 待立项 |

所有实现仍遵循 Contract → Migration → Backend → Unit/Integration/Contract → Real API → Acceptance；当前 2.10-A/B/C/D 均不引入数据库结构变更。