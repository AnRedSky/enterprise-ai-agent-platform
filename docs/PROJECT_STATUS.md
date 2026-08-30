# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.10-II Enterprise Operations Console / Operator Governance 开发中**
- 当前任务：**II-01 Backend Operator Action Governance**
- 最近完成：**Phase 2.10-I Runtime Notification Lifecycle / Provider / Metrics / Alert / Export / Operational Audit 全链路收口**

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
- Phase 2.10-I Runtime Notification Lifecycle、Worker tenant/consumer-group Claim isolation、Retry/Dead Letter/Fallback、SLO/Metrics、Canonical Metrics Export、OpenTelemetry SDK Telemetry、Operational Audit 已完成，并已通过本地实际 Real Gate。

## 3. Phase 2.10-I 收口证据

开发者本地反馈确认：

```text
Runtime targeted unit：13 passed
Runtime / Enterprise Real API Acceptance：6 passed
Phase 2.10-I Runtime Lifecycle Gate：completed
```

最终 Gate 已验证：

```text
Alert Evaluation
→ Firing / Recovery
→ Notification Policy
→ Group / Dedup / Cooldown
→ Provider Routing
→ Worker Claim
→ Claim Competition
→ Outcome
→ Retry / Dead Letter
→ Fallback / Fallback Exhaustion
→ SLO / Metrics
→ Prometheus / OTLP Export
→ Audit
```

Gate 只负责服务状态探测、测试上下文自动生成、验收执行与清理，不自动启动或停止 API、Scheduler、Worker、PostgreSQL、Redis；测试数据自动创建和清理，不要求手工填写测试信息。

## 4. Phase 2.10-II 当前任务

### II-01 Operator Action Governance
状态：**Backend Contract / Domain Adapter / API Contract 已实现，等待本地 Unit / Migration / Real API 验证。**

已实现：
- Workflow Execution Run / Cancel / Retry / Resume 统一 Operator Action API；
- Trigger Enable / Disable / Delete / Invoke 统一 Operator Action API；
- 后端统一返回操作可用性、状态与治理属性；
- 高风险操作统一要求 `confirm=true`；
- Retry / Trigger Invoke 要求 `Idempotency-Key`；
- 新增 tenant-scoped Operator Action 幂等持久化事实；
- Operator Action 复用现有 `WorkflowExecutionService` / `WorkflowTriggerService`，不复制生命周期状态机；
- Operator Action 结果写入现有 `AuditLog`，保留 actor、tenant、resource、action、outcome 与 Execution 关联；
- 已新增 Unit / API Contract 测试与独立 Unit Gate；
- Unit Gate 不自动启动或停止任何服务，也不要求人工填写测试数据。

尚未宣称完成：
- 本地 Alembic `upgrade head` 尚未由本轮开发反馈确认；
- 本地 Unit / API Contract 尚未由本轮开发反馈确认；
- Real API / Browser Acceptance 尚未执行。

正式阶段文档：`docs/02-phases/PHASE_2_10_II.md`

## 5. 长期任务推进

LT-01 Enterprise Integration / Event Infrastructure：**核心 Event / Delivery / Webhook / Runtime Integration 已完成当前主线，Phase 2.10-I 已完成运维收口，后续转为回归维护。**

LT-03 Enterprise Operations Console：**进入 Phase 2.10-II 开发，当前正在完成 II-01 Operator Action Governance，随后推进 Global Runtime Operations、Worker/Scheduler Diagnostics、Audit/Trace Correlation 与 Controlled Batch Operations。**

LT-02 / LT-04 / LT-05 / LT-06 / LT-07 / LT-08 / LT-09 / LT-10：继续保持待立项或候选状态；不得在没有正式 Phase、Contract、代码和验收证据前提前标记为开发中。

## 6. 下一执行顺序

```text
① 本地 Alembic upgrade head
② II-01 Unit / API Contract
③ II-01 Real API tenant boundary / confirmation / idempotency / audit
④ Backend Regression
⑤ Frontend API Types / UI
⑥ Frontend Regression / Build
⑦ Browser E2E（范围需要时）
⑧ 更新 Phase / Acceptance / Long-term Status
⑨ 原子提交 main
```