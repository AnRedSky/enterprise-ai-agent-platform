# Phase 2.10-I RuntimeOperations Audit 查询入口缺失

## 发生时间
2026-08-30

## 现象
Phase 2.10-I Runtime Notification Lifecycle Real Acceptance 在验证 `fallback exhausted → Notification DLQ → SLO/Metrics → Audit` 完整链路时失败：

```text
AttributeError: 'RuntimeOperationsService' object has no attribute 'audit_list'
```

失败位置为 `tests/api_real/test_runtime_notification_fallback_exhausted_acceptance.py` 的 tenant isolation 断言。

## 根因
`RuntimeOperationAudit` 已存在持久化模型，`RuntimeOperationsEnterpriseService` 也已经提供 `audit_list()`，但基础 `RuntimeOperationsService` 只有 DLQ / SLO / metrics 等 Runtime Durable facts 查询，没有正式的 tenant-scoped Audit 查询入口。

Acceptance 直接使用 Runtime 基础服务验证 Audit tenant boundary，导致运行时公开的事实查询边界与验收所依赖的服务入口不一致。

同时，Enterprise Service 中原有 `audit_list()` 自己构造查询，存在维护第二套 Audit 查询规则的风险。

## 修复
- 在 `RuntimeOperationsService` 增加正式的 `audit_list(tenant_id, limit)` 查询入口；
- 查询强制 `tenant_id` 条件，并将返回数量限制在 1~1000；
- 按 `created_at DESC, id DESC` 稳定排序；
- `RuntimeOperationsEnterpriseService.audit_list()` 改为复用基础服务入口，消除重复查询实现；
- 增加单元测试，验证 tenant scope 与 limit 上界。

## 验证要求
本修复需要在开发者本地重新执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_runtime_metric_contract.py tests/unit/test_runtime_telemetry.py
uv run pytest -q -m real_api `
  tests/api_real/test_alert_notification_runtime_acceptance.py `
  tests/api_real/test_runtime_notification_fallback_exhausted_acceptance.py `
  tests/api_real/test_webhook_delivery_claim_acceptance.py `
  tests/api_real/test_runtime_operations_acceptance.py `
  tests/api_real/test_runtime_enterprise_acceptance.py `
  --tb=short
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\03_alert_notification_lifecycle_real_gate.ps1
```

Real Gate 仍不得自动启动或停止 API、Scheduler、Worker、PostgreSQL、Redis；缺失服务必须保持 `NOT EXECUTED` 并输出标准启动提示。
