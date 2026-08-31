# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.10-II Enterprise Operations Console / Operator Governance 开发中**
- 当前任务：**II-06 Runtime Audit Query Backend 第一切片实现**
- 最近完成：**II-01 Backend Operator Action Governance**、**II-02 Global Runtime Operations**、**II-03 Worker / Scheduler Diagnostics 第一切片**、**II-04 Audit / Trace Correlation Backend 第一切片**、**II-05 Controlled Batch Operations Backend 第一切片**。

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
- Phase 2.10-II / II-05 Controlled Batch Operations Backend 第一切片已实现，并已通过开发者本地 Unit / API Contract / Real PostgreSQL Acceptance 反馈。

## 3. II-06 当前状态

已实现第一切片：

- `RuntimeOperationsService.audit_query`：tenant-scoped、数据库分页、稳定排序；
- 支持 action / resource_type / resource_id / outcome 精确过滤；
- 支持 since / until 时间窗口；
- 明确拒绝反向时间窗口；
- 新增 `GET /api/v1/runtime/operations/audit/query`；
- 不新增数据库表、不新增 Audit 生命周期、不复制既有 AuditLog / Operator Action 事实；
- 新增 Unit / API Contract 测试与独立 Unit Gate。

当前未宣称：

- II-06 第一切片尚未由开发者本地执行 Unit Gate；
- II-06 尚未标记 Acceptance Passed；
- Real PostgreSQL / Real API 是否需要执行将在 Unit / Contract 稳定后根据查询范围决定。

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
① 本地执行 II-06 Runtime Audit Query Unit Gate
② Backend Regression
③ 若 Unit / Contract / Regression 全部通过，再决定是否补充 Real PostgreSQL / Real API Acceptance
④ 收口 II-06 第一切片
⑤ 评估 II-06 第二切片或下一 Backend 主线任务
⑥ 继续实现，不提前进入 Frontend / Browser 工作
```
