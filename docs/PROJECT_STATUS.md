# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.10-II Enterprise Operations Console / Operator Governance 开发中**
- 当前任务：**Backend Operator Audit Governance 查询入口接线、真实验收与下一项 Operator Governance 能力推进**。
- 最近完成：**II-01 Backend Operator Action Governance**、**II-02 Global Runtime Operations**、**II-03 Worker / Scheduler Diagnostics 第一切片**、**II-04 Audit / Trace Correlation Backend 第一切片**、**II-05 Controlled Batch Operations Backend 第一切片**、**II-06 Runtime Audit Query Backend 第一切片与查询性能强化**、**II-07 actor 精确过滤、actor + action、action + outcome 组合过滤硬化与查询响应契约硬化**、**Runtime Audit / Trace Correlation 响应 Contract 硬化与历史审计关联硬化**、**Operator Audit Query Service / API Contract 第一实现**。

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
- Operator Audit Query API Contract 已实现，响应模型明确为 `OperatorAuditQueryResponse` / `OperatorAuditItem`，查询参数包含 page、page_size、action、resource_type、resource_id、actor_id、status、workflow_execution_id、trace_id、since、until。

## 3. Backend 最近验收基线

开发者已反馈：

```text
Runtime correlation Unit: 9 passed
Runtime correlation API Contract: 6 passed
Runtime correlation Real PostgreSQL Acceptance: 1 passed
Runtime correlation targeted regression: 17 passed
Backend default regression: 1031 passed, 3 skipped, 73 deselected
```

以上为开发者本地实际执行结果。

当前 Operator Audit Governance Gate 首次执行发现应用装配缺口：`operator_audit.py` 已实现，但 `app.main` 未注册该 Router，导致 5 个 API Contract 断言全部从路由不存在开始失败。该问题已在 `main` 修复，并记录于 `docs/04-errors/2026-09-01-operator-audit-route-registration.md`；修复后的 Gate 尚未由开发者本地执行，因此不预填通过结果。

## 4. 当前 Backend 任务

### Operator Audit Governance 查询入口 — 已修复，等待本地 Gate

- `OperatorAuditQueryService` 继续以 `AuditLog` 为唯一 Operator Action 审计事实源；
- 查询 tenant scope 完全来自认证 Claims，不接受客户端 `tenant_id`；
- `Operator Audit Query API` 使用 GET-only Router，响应 Contract 明确、过滤边界显式；
- 已修复 `backend/app/main.py` 漏注册 `runtime_operator_audit_router` 的应用装配错误；
- 错误记录：`docs/04-errors/2026-09-01-operator-audit-route-registration.md`；
- 下一步先执行 `24_operator_audit_governance_gate.ps1` 完成 Unit / API Contract / Real PostgreSQL / targeted regression 验证，再扫描下一项 Operator Governance / Audit 真实业务缺口。

## 5. Backend 下一执行顺序

```text
① 开发者执行 24_operator_audit_governance_gate
② 若通过，确认 warning-free 与 Real PostgreSQL Acceptance
③ 扫描 Operator Audit Governance 的真实业务缺口
④ Backend-first 推进下一项 Operator Governance / Audit 能力
⑤ 前端测试与 Browser E2E 暂不作为当前 Backend 主线阻塞条件
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
