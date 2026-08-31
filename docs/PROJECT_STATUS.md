# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.10-II Enterprise Operations Console / Operator Governance 开发中**
- 当前任务：**Backend-first Runtime Audit / Trace Correlation Contract 硬化与后续 Operator Governance 能力推进**。
- 最近完成：**II-01 Backend Operator Action Governance**、**II-02 Global Runtime Operations**、**II-03 Worker / Scheduler Diagnostics 第一切片**、**II-04 Audit / Trace Correlation Backend 第一切片**、**II-05 Controlled Batch Operations Backend 第一切片**、**II-06 Runtime Audit Query Backend 第一切片与查询性能强化**、**II-07 actor 精确过滤、actor + action、action + outcome 组合过滤硬化与查询响应契约硬化**、**Runtime Audit / Trace Correlation 响应 Contract 硬化**。

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
- Runtime Audit / Trace Correlation 响应 Contract 已从 `list[Any]` 收紧为明确的 Trace / Audit Item 类型，并增加 Trace ID 输入边界。

## 3. Backend 最近验收基线

开发者已反馈：

```text
Runtime lifecycle targeted API: 2 passed
Backend default regression: 1016 passed, 3 skipped, 73 deselected
Runtime Audit action + outcome hardening: Unit/API 9 passed + Real PostgreSQL 1 passed
Runtime Audit query contract hardening: Unit/API 9 passed + Real PostgreSQL 1 passed
```

以上均为开发者本地实际执行结果；本轮新增 Runtime Correlation Contract Gate 尚未由开发者本地执行，因此不预填通过结果。

## 4. 当前 Backend 任务

### Runtime Audit / Trace Correlation Contract 硬化 — 已实现，等待本地 Gate

- `RuntimeCorrelationResponse` 的 Trace 分页使用 `RuntimeCorrelationTracePage`；
- Audit 分页使用 `RuntimeCorrelationAuditPage`；
- OpenAPI 明确暴露 `WorkflowTraceItem` 与 `AuditLogItem`；
- `/api/v1/runtime/correlations/traces/{trace_id}` 增加 1..128 长度边界；
- 继续禁止客户端传递 `tenant_id`，tenant scope 只来自认证 Claims；
- 新增 `tests/api_contract/test_runtime_correlations_contract.py`；
- 新增 `scripts/test/phase-2.10/23_runtime_correlation_contract_hardening_gate.ps1`；
- 工程问题记录于 `docs/04-errors/2026-08-31-runtime-correlation-weak-response-contract.md`。

## 5. Backend 下一执行顺序

```text
① 开发者执行 23_runtime_correlation_contract_hardening_gate
② 若通过，执行 backend uv run pytest -q
③ 继续扫描 II-04 Audit / Trace Correlation 的真实业务缺口
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
