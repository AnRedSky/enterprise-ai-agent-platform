# Phase 2.10 — Enterprise Integration Event Operations

## 目标
在 Phase 2.9 已形成 Durable Integration Event → Reliable Delivery → Webhook → Replay/Audit 基础能力后，建设面向企业运维的统一事件操作面：查询、投递诊断、Replay、审计、指标、SLO 与死信治理。

## 2.10-A / B
已实现 Integration Event 查询、summary、Delivery 查询，全部强制 tenant scope。

## 2.10-C Retry / Replay Operations
状态：**第一切片已实现**。

- `POST /api/v1/runtime/integration-events/deliveries/{delivery_id}/replay`
- 仅 admin 可执行。
- tenant + delivery 双重隔离。
- 仅允许 `delivered` / `dead_letter` replay；pending/running 返回 409。
- replay 重新进入 `pending`，清理旧 lease、delivery timestamp 与错误状态。
- 通过现有 `WebhookDeliveryRepository.replay()` 写入不可变 `WebhookDeliveryAudit(action=replay)`。
- API 不直接执行网络请求，由 Worker 后续领取。

## 2.10-D Delivery Audit Query
状态：**第一切片已实现**。

- `GET /api/v1/runtime/integration-events/deliveries/{delivery_id}/audits`
- tenant + delivery scope。
- 分页查询 delivered / retry / dead_letter / replay 等不可变事实。

## 2.10-E Operations Console
状态：**第一切片已实现**。

- `GET /api/v1/runtime/operations/overview`。
- 统计窗口支持 1 / 24 / 168 小时。
- 返回事件状态、Delivery 状态、重试、死信、成功率、99% SLO、错误预算和 P95 延迟。
- 前端 `/runtime/operations` 提供 Event / Delivery / SLO / Dead Letter 聚合视图。

## 2.10-F Metrics / SLO
状态：**增强切片已实现**。

新增：
- `GET /api/v1/runtime/operations/dimensions`；
- 按 Event Type + Destination 聚合 Delivery Durable Facts；
- 当前 Webhook HTTP Provider 作为 canonical provider dimension `webhook_http`；
- 返回状态分布、Retry、Dead Letter 和成功率；
- 维度查询继续强制 tenant scope；
- `GET /api/v1/runtime/operations/alerts` 提供可解释的 SLO / Retry / Dead Letter 告警评估。

指标仍全部从 PostgreSQL Durable Event / Delivery facts 实时计算，不建立平行事实源。

后续：时间序列、Provider 可配置注册表、Prometheus/OpenTelemetry export。

## 2.10-G Dead Letter Management
状态：**增强切片已实现**。

- tenant-scoped Dead Letter 查询；
- 分页；
- attempt / HTTP / error / lease / timestamps；
- 单条 Replay；
- 新增 `POST /api/v1/runtime/operations/dead-letters/replay` 批量 Replay；
- 一次最多 100 个 Delivery ID；
- 重复 ID 自动去重；
- 每项独立处理，成功与拒绝结果分别返回；
- Replay 仍只重新入队，不同步执行网络请求；
- 每次成功 Replay 均通过 canonical Repository 产生不可变 Audit Fact。

后续：人工关闭/归档、失败原因分类、重试策略诊断与批量操作审计摘要。

## 2.10-H Runtime Operational Acceptance
状态：**Acceptance Gate 已实现，待本地 Real PostgreSQL 执行**。

Acceptance 脚本：

`backend/scripts/test/phase-2.10/01_runtime_operations_real_gate.ps1`

Acceptance 测试：

`backend/tests/api_real/test_runtime_operations_acceptance.py`

必须一次性验证：

1. tenant A / B Event 隔离；
2. Delivery 隔离；
3. Dead Letter 隔离；
4. Overview 只统计当前 tenant；
5. Event Type + Destination dimension 只统计当前 tenant；
6. SLO 来自真实 PostgreSQL Durable facts；
7. SLO breach / retry / dead-letter 告警可解释；
8. Dead Letter Replay 重新进入 `pending`；
9. Replay Audit 可追溯且 tenant scoped；
10. 后续 Worker 仍负责实际网络投递，不由 Operations API 直接调用 Webhook。

Gate 不启动或停止 API、Worker、Scheduler、Redis、PostgreSQL；测试数据自动生成和清理，不要求人工填写测试信息。

## 约束
- Operations API 不绕过 Repository 直接修改投递状态。
- 所有运维动作必须 tenant-scoped。
- 查询无副作用。
- Replay 只重新入队，不同步执行网络请求。
- 所有 Replay 必须产生不可变审计事实。
- Metrics 必须从已有 Durable Event / Delivery 事实聚合，不建立平行事实源。
- 告警计算必须是确定性的、可解释的，并可从 Durable facts 重算。
