# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.10-II Enterprise Operations Console / Operator Governance 开发中**
- 当前任务：**II-07 Runtime Audit Query 运维主体过滤与主体 + 动作组合过滤硬化**
- 最近完成：**II-01 Backend Operator Action Governance**、**II-02 Global Runtime Operations**、**II-03 Worker / Scheduler Diagnostics 第一切片**、**II-04 Audit / Trace Correlation Backend 第一切片**、**II-05 Controlled Batch Operations Backend 第一切片**、**II-06 Runtime Audit Query Backend 第一切片与查询性能强化**、**II-07 actor 精确过滤第一切片**。

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
- Phase 2.10-II / II-06 Runtime Audit Query Backend 第一切片与 `0050_runtime_audit_query_indexes` 查询性能强化已完成，并已通过开发者本地 Unit / API Contract / Real PostgreSQL Acceptance 反馈。

## 3. II-07 当前状态

### 第一切片：actor 精确过滤 — 已完成

- 在既有 `RuntimeOperationsService.audit_query` 上增加 `actor` 精确过滤；
- tenant scope 仍完全由认证 Claims 决定，不接受 `tenant_id` 查询参数；
- 复用既有 `(tenant_id, actor, created_at)` 复合索引；
- `GET /api/v1/runtime/operations/audit/query` 增加可选 `actor` 参数，最大长度 128；
- 新增 Unit、API Contract 与真实 PostgreSQL tenant-isolation / actor-filter acceptance 覆盖；
- `18_runtime_audit_actor_filter_unit_gate.ps1` 与 `19_runtime_audit_actor_filter_real_gate.ps1` 已完成开发者本地验证。

### 当前后续硬化：actor + action 组合过滤

已实现代码级第一版：

- 新增 `0051_runtime_audit_actor_action_index`；
- `RuntimeOperationAudit` 模型同步声明 `(tenant_id, actor, action, created_at)` 复合索引；
- Unit 覆盖 actor + action 同时过滤且保持 tenant scope；
- Real PostgreSQL Acceptance 覆盖主体 + 动作组合过滤，以及相同 actor/action 的跨租户隔离；
- 新增 `20_runtime_audit_actor_action_hardening_gate.ps1`，自动执行 migration head、`alembic upgrade head`、Unit/API Contract 与 Real PostgreSQL Acceptance；
- Gate 不自动启动或停止任何服务，测试身份和业务事实均自动生成。

**开发者本地执行 `20_runtime_audit_actor_action_hardening_gate.ps1` 后，再决定是否进入下一项审计运维查询能力；在真实结果返回前不预填通过状态。**

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
① 执行 20_runtime_audit_actor_action_hardening_gate.ps1
② 执行 Backend targeted regression
③ 根据真实结果检查 II-07 是否存在下一项审计查询缺口
④ 继续 II-07 后续 Backend 能力
```
