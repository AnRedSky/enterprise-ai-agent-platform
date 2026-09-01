# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.10-II Enterprise Operations Console / Operator Governance 开发中**
- 当前任务：**Operator Action → Audit → Result Resource → Execution/Trace 治理闭环与数据库事实源对齐**。
- 最近完成：**II-01 Backend Operator Action Governance**、**II-02 Global Runtime Operations**、**II-03 Worker / Scheduler Diagnostics 第一切片**、**II-04 Audit / Trace Correlation Backend 第一切片**、**II-05 Controlled Batch Operations Backend 第一切片**、**II-06 Runtime Audit Query Backend 第一切片与查询性能强化**、**II-07 actor 精确过滤、actor + action、action + outcome 组合过滤硬化与查询响应契约硬化**、**Runtime Audit / Trace Correlation 响应 Contract 硬化与历史审计关联硬化**、**Operator Audit Query Service / API Contract 第一实现**、**Operator Audit 管理员访问治理**、**Canonical Operator Audit 查询索引事实源对齐**。

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
- Phase 2.10-II / II-06 Runtime Audit Query Backend 第一切片与 `0050_runtime_audit_query_indexes` 查询性能强化已完成，并已通过开发者本地 Unit / API Contract / Real PostgreSQL Acceptance 反馈；
- Phase 2.10-II / II-07 Runtime Audit Query 主体、组合过滤及响应契约硬化已完成 Backend 实现；
- Runtime Audit / Trace Correlation 响应 Contract 已从 `list[Any]` 收紧为明确的 Trace / Audit Item 类型，并增加 Trace ID 输入边界；
- Runtime Audit / Trace Correlation 历史审计恢复路径已补齐：正式 `workflow_execution_id` 优先，缺失时通过 tenant-scoped `trace_id` 恢复当前 Workflow Execution，不猜测旧 `execution_id` 映射；
- Operator Audit Query Service 已基于 AuditLog 唯一事实源实现 tenant-scoped 分页、精确过滤和时间窗口校验；
- Operator Audit Query API Contract 已实现，响应模型明确为 `OperatorAuditQueryResponse` / `OperatorAuditItem`，查询参数包含 page、page_size、action、resource_type、resource_id、actor_id、status、workflow_execution_id、trace_id、since、until；
- Operator Audit Query 已增加 admin-only 访问治理；
- `0051_operator_audit_query_indexes` 已将 Canonical Operator Audit 常用 tenant-scoped 查询索引正式落到 `audit_logs`。

## 3. 最新本地反馈与根因

开发者执行 `26_operator_audit_query_performance_gate.ps1` 时，targeted regression 暴露 `audit_logs.operator_action_id` 缺失，以及 Runtime Audit / Trace Correlation 单元测试 mock 未覆盖新增的直接 Operator Action → Audit 查询调用。此前 Gate 的 `alembic upgrade head` 还暴露 migration graph 存在多个 head。

根因进一步确认：`0048_operator_action_audit_lineage`、`0051_operator_audit_query_indexes` 与 `0053_operator_action_result_resource_type` 所在 migration 链存在多个独立分支；`0048` 还依赖 `0049` 创建的 Operator Action 表，却没有声明 Alembic `depends_on`。

## 4. 当前 Backend 修复

- 为 `0048_operator_action_audit_lineage` 增加 `depends_on = "0049_operator_action_idempotency"`，确保全新数据库按 DDL 依赖顺序执行；
- 新增 `0054_merge_operator_governance_heads`，一次性合并 `0053_operator_action_result_resource_type`、`0051_operator_audit_query_indexes`、`0048_operator_action_audit_lineage` 三个 Operator Governance head；
- 恢复原有 `0053_operator_action_result_resource_type`，保留其结果类型回填与失败结果清理逻辑；
- 新增 PostgreSQL Acceptance，验证 `audit_logs.operator_action_id`、`operator_action_idempotencies.result_resource_type` 以及 Operator Action → AuditLog 外键真实存在；
- 修正 Runtime Audit / Trace Correlation 单元测试 mock，使其与直接 Operator Action → Audit 查询行为一致；
- 更新 `26_operator_audit_query_performance_gate.ps1`，显式验证单一 migration head，并把治理闭环 PostgreSQL schema acceptance 纳入 Gate；
- 错误记录：`docs/04-errors/2026-09-01-operator-governance-migration-head-and-schema-drift.md`。

## 5. 下一执行顺序

```text
① 开发者重新执行 Operator Governance Gate
② 确认 Alembic 单一 head + migration upgrade
③ 确认 Operator Action → Audit → Result Resource PostgreSQL Acceptance
④ 扫描 Execution / Trace 端到端治理链仍存在的真实业务缺口
⑤ Backend-first 推进下一项 Operator Governance / Audit 能力
⑥ 前端测试与 Browser E2E 暂不作为当前 Backend 主线阻塞条件
```

## 6. Backend 验收规则

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
