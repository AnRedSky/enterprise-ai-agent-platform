# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.10-II Enterprise Operations Console / Operator Governance 开发中**
- 当前任务：**II-05 Controlled Batch Operations Backend 第一切片**
- 最近完成：**II-01 Backend Operator Action Governance**、**II-02 Global Runtime Operations**、**II-03 Worker / Scheduler Diagnostics 第一切片**、**II-04 Audit / Trace Correlation Backend 第一切片** 与 Phase 2.10-I Runtime Notification Lifecycle 全链路收口。

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
- Phase 2.10-II / II-02 Global Runtime Operations 已完成 Backend Unit / Real PostgreSQL Gate 与完整 Backend Regression 本地验证；
- Phase 2.10-II / II-03 Worker / Scheduler Diagnostics Backend 与 Frontend 第一切片已实现；
- Phase 2.10-II / II-04 Audit / Trace Correlation Backend 第一切片已实现，复用现有 Workflow Execution / Workflow Trace / AuditLog / Operator Action Durable Facts；
- Phase 2.10-II / II-05 Controlled Batch Operations Backend 第一切片已实现，复用现有 Operator Action Governance，不新增 Workflow / Trigger 生命周期。

## 3. II-05 当前状态

已实现：

- `BatchOperatorActionService`：统一编排 tenant-scoped 批量 Operator Action；
- 支持现有 `workflow_execution` / `workflow_trigger` Operator Action；
- 单批次最多 100 个资源；禁止重复资源 ID；
- 高风险动作继续由 `OperatorActionGovernanceService` 统一执行 `confirm=true` 校验；
- Retry / Trigger Invoke 继续复用既有 Idempotency Contract，并从批次键稳定派生单项幂等键；
- 每个项目独立返回 `succeeded` / `rejected` / `failed`，允许同批次合法项目继续执行；
- 所有实际状态变更继续委托 `WorkflowExecutionService` / `WorkflowTriggerService`；
- 新增 `/api/v1/runtime/operator-actions/batch` HTTP Contract；
- Unit / API Contract / Real PostgreSQL Acceptance 测试与独立 Gate 已提交。

当前未宣称：

- II-05 Unit Gate 尚未由开发者本地执行；
- II-05 Real PostgreSQL Acceptance 尚未由开发者本地执行；
- II-05 尚未标记 Acceptance Passed；
- Frontend 回归不作为本阶段 Backend 验收阻塞条件。

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
① 本地执行 II-05 Controlled Batch Operations Unit Gate
② 本地执行 II-05 Controlled Batch Operations Real Gate
③ Backend Regression
④ 收口 II-05 Acceptance
⑤ 检查 II-06 下一 Backend 主线任务
⑥ 继续实现，不提前进入 Frontend / Browser 工作
```
