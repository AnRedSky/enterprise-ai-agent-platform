# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.10-II Enterprise Operations Console / Operator Governance 开发中**
- 当前任务：**II-02 Global Runtime Operations**
- 最近完成：**II-01 Backend Operator Action Governance** 与 Phase 2.10-I Runtime Notification Lifecycle 全链路收口。

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
- Phase 2.10-II / II-01 Operator Action Governance 已完成本地验证。

## 3. Phase 2.10-I 收口证据

开发者本地反馈确认：

```text
Runtime targeted unit：13 passed
Runtime / Enterprise Real API Acceptance：6 passed
Phase 2.10-I Runtime Lifecycle Gate：completed
```

## 4. Phase 2.10-II / II-01 完成证据

开发者本地反馈确认：

```text
Alembic head：0049_operator_action_idempotency
Operator Action unit + API contract：16 passed
Operator Action Real PostgreSQL acceptance：2 passed
Full backend regression：971 passed, 3 skipped, 68 deselected
```

II-01 的核心约束已经落地：

- Workflow Execution Run / Cancel / Retry / Resume 统一 Operator Action API；
- Trigger Enable / Disable / Delete / Invoke 统一 Operator Action API；
- 高风险操作统一要求 `confirm=true`；
- Retry / Trigger Invoke 要求 `Idempotency-Key`；
- tenant-scoped Operator Action 幂等持久化事实；
- Operator Action 复用现有 `WorkflowExecutionService` / `WorkflowTriggerService`，不复制生命周期状态机；
- Operator Action 结果写入现有 `AuditLog`。

## 5. Phase 2.10-II 当前任务

### II-02 Global Runtime Operations
状态：**Backend Domain / API Contract 与 Frontend API Types / Operations UI 已实现，等待本地 Frontend / Backend 验证。**

已实现：
- `GlobalRuntimeOperationsService`：只读聚合现有 Workflow / Execution / Frontier / Trigger Durable facts；
- Execution 状态、active/recovery、最近执行统一视图；
- Workflow / Trigger 状态摘要；
- Worker Frontier running / pending / lease / expired lease / active owner 统计；
- Scheduler durable backlog 与 enabled scheduled trigger 统计；
- `workflow_id` / `agent_id` / `trigger_id` / `execution_id` / `execution_status` 关联查询 Contract；
- `/api/v1/runtime/global` read-only API；
- Worker / Scheduler process liveness 在没有 durable heartbeat fact 时明确返回 `unknown + NO_DURABLE_HEARTBEAT_FACT`，不伪造服务健康状态；
- Frontend `runtimeOperationsApi.global` 类型化接入 Backend Contract；
- `/runtime/operations/global` 全局 Runtime Operations 只读页面；
- Frontend Component Contract 测试与独立 Phase 2.10-II Frontend Gate；
- Backend Unit / API Contract / PostgreSQL Real Acceptance 测试；
- Backend 独立 Unit / Real Gate，均不自动启动或停止 API、Scheduler、Worker、PostgreSQL、Redis，Acceptance 数据自动生成和清理。

当前未宣称：
- II-02 Frontend Unit / Build 尚未由本轮开发反馈执行；
- II-02 Backend Unit / Real API 尚未由本轮开发反馈执行；
- Browser E2E 尚未执行；
- II-02 尚未标记 Acceptance Passed。

正式阶段文档：`docs/02-phases/PHASE_2_10_II.md`

## 6. 长期任务推进

LT-01 Enterprise Integration / Event Infrastructure：**核心 Event / Delivery / Webhook / Runtime Integration 已完成当前主线，Phase 2.10-I 已完成运维收口，后续转为回归维护。**

LT-03 Enterprise Operations Console：**Phase 2.10-II 正在推进；II-01 已完成，II-02 Backend 与 Frontend 第一切片已实现，当前进入本地验证与后续 II-02 联调。随后推进 II-03 Worker/Scheduler Diagnostics、II-04 Audit/Trace Correlation、II-05 Controlled Batch Operations。**

LT-02 / LT-04 / LT-05 / LT-06 / LT-07 / LT-08 / LT-09 / LT-10：继续保持待立项或候选状态；不得在没有正式 Phase、Contract、代码和验收证据前提前标记为开发中。

## 7. 下一执行顺序

```text
① II-02 Frontend targeted Unit / Build
② II-02 Backend Unit / Real PostgreSQL / tenant boundary
③ Backend Regression
④ Frontend Regression / Build
⑤ Browser E2E（范围需要时）
⑥ II-02 Acceptance
⑦ 进入 II-03 Worker / Scheduler Diagnostics
```
