# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.10-II Enterprise Operations Console / Operator Governance 开发中**
- 当前任务：**II-06 Runtime Audit Query Backend 查询性能强化**
- 最近完成：**II-01 Backend Operator Action Governance**、**II-02 Global Runtime Operations**、**II-03 Worker / Scheduler Diagnostics 第一切片**、**II-04 Audit / Trace Correlation Backend 第一切片**、**II-05 Controlled Batch Operations Backend 第一切片**、**II-06 Runtime Audit Query Backend 第一切片**。

开发严格基于远端 `main`，不创建功能分支。

## 2. 已完成能力
- Phase 2.7 Advanced Workflow 主线生产能力完成；
- Durable Workflow / Resume / Frontier / Scheduler 基础设施完成；
- Phase 2.8 Delegation Contract、Durable Entity、Claim、Worker Bridge、generation fencing、timeout/cancel、Audit/Trace、B6 multi-worker Runtime 已完成并通过本地 Real Gate；
- Phase 2.9-A Event Contract、2.9-B Durable Event Persistence、2.9-C Reliable Delivery、2.9-D Webhook Integration、2.9-E Runtime Integration 已完成对应真实验收；
- Phase 2.10-A/B/C/D Event、Delivery、Replay、Audit 运维能力已实现；
- Phase 2.10-E Operations Console 第一切片已实现；
- Phase 2.10-F Metrics / SLO 已增强到 Event Type + Destination + Provider 维度及确定性告警；
- Phase 2.10-G Dead Letter 已增强到批量 Replay；
- Phase 2.10-H Runtime Operational Acceptance Gate 已实现；
- Phase 2.10-I Runtime Notification Lifecycle、Worker tenant/consumer-group Claim isolation、Retry/Dead Letter/Fallback、SLO/Metrics、Canonical Metrics Export、OpenTelemetry SDK Telemetry、Operational Audit 已完成，并已通过本地实际 Real Gate；
- Phase 2.10-II / II-01 Operator Action Governance 已完成本地验证；
- Phase 2.10-II / II-02 Global Runtime Operations 已完成本地 Backend Unit / Real PostgreSQL 验证；
- Phase 2.10-II / II-03 Worker / Scheduler Diagnostics Backend 第一切片已实现；
- Phase 2.10-II / II-04 Audit / Trace Correlation Backend 第一切片已实现；
- Phase 2.10-II / II-05 Controlled Batch Operations Backend 第一切片已实现，并已通过开发者本地 Unit / API Contract / Real PostgreSQL Acceptance 反馈；
- Phase 2.10-II / II-06 Runtime Audit Query Backend 第一切片已通过开发者本地 Unit / API Contract / Real PostgreSQL Acceptance 反馈，现进入查询性能强化。

## 3. II-06 当前状态

第一切片已完成：

- `RuntimeOperationsService.audit_query`：tenant-scoped、数据库分页、稳定排序；
- 支持 action / resource_type / resource_id / outcome 精确过滤；
- 支持 since / until 时间窗口；
- 明确拒绝反向时间窗口；
- 新增 `GET /api/v1/runtime/operations/audit/query`；
- 不新增 Audit 生命周期、不复制既有 AuditLog / Operator Action 事实；
- Unit / API Contract 与 Real PostgreSQL tenant isolation / operational filtering 已完成开发者本地反馈验收。

当前进行第二切片：

- 新增 `0050_runtime_audit_query_indexes` Alembic migration；
- 为 tenant + resource、tenant + outcome、tenant + actor 的常用审计查询组合建立复合索引；
- 修复真实验收中的 `datetime.utcnow()` 弃用警告；
- 新增独立 Hardening Unit / Real Gate；
- 不自动启动任何服务，不要求手工填写测试身份或业务 ID。

## 4. Backend 验收规则

当前后端任务只以以下证据作为开发验收依据：

```text
Backend Unit
  ↓
API Contract
  ↓
必要时 Real PostgreSQL / Real API Acceptance
  ↓
Backend Regression
```

Frontend 页面回归、Frontend Build、Browser E2E 不作为 Backend 主线开发阻塞条件。

所有 Gate 均禁止自动创建、启动、重启或停止 API、Scheduler、Worker、PostgreSQL、Redis；真实 Acceptance 必须自动生成和清理测试身份与业务数据。

## 5. 下一执行顺序

```text
① 执行 II-06 Runtime Audit Query Hardening Unit Gate
② 执行 Backend Regression
③ 在已有本地 PostgreSQL 上执行 Hardening Real Gate
④ 确认 migration head 与复合索引真实存在
⑤ 收口 II-06
⑥ 评估 II-07 下一 Backend 主线能力
```
