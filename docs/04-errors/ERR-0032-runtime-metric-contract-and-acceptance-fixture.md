# ERR-0032 Runtime Metric Contract 部分指标导出与 Real Acceptance fixture 唯一键冲突

## 现象

Phase 2.10-I Runtime Enterprise Acceptance 在真实 PostgreSQL 环境出现两类失败：

1. `RuntimeMetricContract.prometheus()` / `otlp()` 接收到只包含 `runtime.delivery.success_percent` 的合法 canonical 子集时，仍遍历完整指标集合，导致 `KeyError: runtime.delivery.retry_count`。
2. `test_runtime_operations_real_postgres_end_to_end_and_tenant_isolation` 为同一租户、同一 destination、同一 integration event 构造 delivered 与 dead-letter 两条 delivery，违反数据库唯一约束 `uq_webhook_delivery_event_destination`。

## 根因

指标 Contract 的 canonical 名称集合既承担“允许哪些指标”的校验职责，又被错误地当成“本次请求必须提供全部指标”的输入集合。实际 exporter 调用允许按当前可用指标导出合法子集，因此缺失指标不应被索引。

Real Acceptance fixture 则没有遵守 webhook delivery 的幂等事实：同一 `(tenant_id, destination_id, integration_event_id)` 只能对应一个 delivery。为了同时验证 delivered 与 dead-letter，应创建不同的 integration event，而不是复制同一个事件。

## 修复

- `RuntimeMetricContract` 新增统一的 canonical 输入校验，并按 canonical 顺序仅导出本次实际提供的指标；Prometheus 与 OTLP 共用同一入口，保持命名和边界一致。
- Real PostgreSQL acceptance 为 delivered 与 dead-letter delivery 分别创建 integration event，并同步调整事件总数断言。
- 保留未知指标拒绝、非有限数值拒绝、Prometheus tenant label 转义及 OTLP tenant resource 属性约束。

## 预防

- exporter Contract 必须区分“合法指标全集”和“本次采样子集”。
- 真实数据库 fixture 必须遵守生产唯一约束，不能通过重复实体制造不同状态。
-涉及幂等键、tenant boundary、状态机的 acceptance fixture 应优先从数据库约束和领域不变量反向设计。

## 验证边界

本次修复对应本地反馈中的两个失败：

- `tests/api_real/test_runtime_operations_acceptance.py::test_runtime_operations_real_postgres_end_to_end_and_tenant_isolation`
- `tests/api_real/test_runtime_enterprise_acceptance.py::test_runtime_metric_contract_keeps_tenant_boundary_for_both_export_formats`

修复代码已直接提交 `main`；本轮对话中无法直接执行用户本地 PostgreSQL/Redis/Scheduler/Worker 环境，因此不能虚构本地 Real API 通过结果。