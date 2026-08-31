# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.10-II Enterprise Operations Console / Operator Governance 开发中**
- 当前任务：**II-04 Audit / Trace Correlation Backend 第一切片**
- 最近完成：**II-01 Backend Operator Action Governance**、**II-02 Global Runtime Operations**、**II-03 Worker / Scheduler Diagnostics 第一切片** 与 Phase 2.10-I Runtime Notification Lifecycle 全链路收口。

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
- Phase 2.10-II / II-04 Audit / Trace Correlation Backend 第一切片已实现，复用现有 Workflow Execution / Workflow Trace / AuditLog / Operator Action Durable Facts。

## 3. Phase 2.10-I 收口证据

开发者本地反馈确认：

```text
Runtime targeted unit：13 passed
Runtime / Enterprise Real API Acceptance：6 passed
Phase 2.10-I Runtime Lifecycle Gate：completed
```

## 4. Phase 2.10-II / II-01 与 II-02 完成证据

开发者本地反馈确认：

```text
II-01 Alembic head：0049_operator_action_idempotency
II-01 Operator Action unit + API contract：16 passed
II-01 Operator Action Real PostgreSQL acceptance：2 passed
II-01 Full backend regression：971 passed, 3 skipped, 68 deselected
II-02 Global Runtime Operations unit / API contract：8 passed
II-02 Global Runtime Operations Real PostgreSQL acceptance：1 passed
II-02 Full backend regression：979 passed, 3 skipped, 69 deselected
```

II-01 的核心约束已经落地：

- Workflow Execution Run / Cancel / Retry / Resume 统一 Operator Action API；
- Trigger Enable / Disable / Delete / Invoke 统一 Operator Action API；
- 高风险操作统一要求 `confirm=true`；
- Retry / Trigger Invoke 要求 `Idempotency-Key`；
- tenant-scoped Operator Action 幂等持久化事实；
- Operator Action 复用现有 `WorkflowExecutionService` / `WorkflowTriggerService`，不复制生命周期状态机；
- Operator Action 结果写入现有 `AuditLog`。

II-02 的核心约束已经落地：

- `GlobalRuntimeOperationsService` 只读聚合 Workflow / Execution / Frontier / Trigger Durable Facts；
- Agent correlation 复用 `WorkflowVersion.definition.agent_id`；
- Worker / Scheduler liveness 没有 Durable Heartbeat 时统一报告 `unknown + NO_DURABLE_HEARTBEAT_FACT`；
- Global Runtime 查询严格 tenant-scoped；
- 不新增第二套 Workflow / Trigger / Worker / Scheduler 生命周期实现。

## 5. II-03 当前状态

II-03 Backend / Frontend 第一切片已提交，包含：

- Worker Frontier / lease / owner / recent error 只读诊断；
- Scheduler durable backlog / scheduled trigger 摘要；
- `unknown + NO_DURABLE_HEARTBEAT_FACT` 的明确 liveness Contract；
- `/api/v1/runtime/diagnostics/worker`；
- `/api/v1/runtime/diagnostics/scheduler`；
- Global Runtime Operations 页面中的 Worker / Scheduler Diagnostics UI；
- 前端类型化 Diagnostics API；
- Unit / API Contract / Real PostgreSQL Gate 已提交。

开发者本地最新反馈尚未包含 II-03 UI/Correlation 后续交付后的完整 Frontend / Backend Regression，因此不提前宣称新的 Acceptance Passed。

## 6. II-04 当前任务

### Audit / Trace Correlation Backend 第一切片

已实现：

- `RuntimeAuditTraceCorrelationService`：统一只读聚合 Execution / Trace / Audit / Operator Action；
- Execution → Trace / Audit / Operator Action；
- Trace → Execution / Audit / Operator Action；
- Audit → Execution / Trace / Operator Action；
- Operator Action → Execution / Audit / Trace；
- 所有关联查询严格 tenant-scoped；
- Trace / Audit 使用 `created_at + id` 稳定排序与独立分页；
- 不新增第二套 Trace / Audit 存储，不修改现有 Durable Facts；
- 四条只读 Runtime correlation HTTP Contract；
- Unit / API Contract / Real PostgreSQL Acceptance 测试；
- 独立 Unit / Real Gate，Gate 不自动启动或停止任何服务。

当前未宣称：
- II-04 Unit Gate 尚未由开发者本地执行；
- II-04 Real PostgreSQL Acceptance 尚未由开发者本地执行；
- II-04 Frontend Correlation UI 尚未实现；
- Browser E2E 尚未执行；
- II-04 尚未标记 Acceptance Passed。

## 7. 长期任务推进

LT-01 Enterprise Integration / Event Infrastructure：**核心 Event / Delivery / Webhook / Runtime Integration 已完成当前主线，Phase 2.10-I 已完成运维收口，后续转为回归维护。**

LT-03 Enterprise Operations Console：**Phase 2.10-II 正在推进；II-01 与 II-02 已完成，II-03 第一切片已实现，II-04 Backend 第一切片已实现，当前进入本地验证与前端 Correlation UI 阶段。**

LT-02 / LT-04 / LT-05 / LT-06 / LT-07 / LT-08 / LT-09 / LT-10：继续保持待立项或候选状态；不得在没有正式 Phase、Contract、代码和验收证据前提前标记为开发中。

## 8. 下一执行顺序

```text
① II-04 Backend Unit / API Contract Gate
② II-04 Backend Real PostgreSQL / tenant boundary Gate
③ Backend Regression
④ II-04 Frontend API Types / Correlation UI
⑤ Frontend targeted Unit / Build
⑥ Frontend Regression / Build
⑦ Browser E2E（范围需要时）
⑧ II-04 Acceptance
⑨ 进入 II-05 Controlled Batch Operations
```
