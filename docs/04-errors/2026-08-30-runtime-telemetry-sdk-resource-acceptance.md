# 2026-08-30 Runtime Telemetry SDK Resource Acceptance 断言失败

## 现象

本地 Real API Acceptance 在 `test_runtime_enterprise_registry_metrics_export_audit_are_tenant_scoped` 失败：

```text
assert telemetry_resource == RuntimeMetricContract.otel_sdk_resource()
AssertionError: assert {'telemetry.sdk....', 'service.version': '0.1.0'} == {'service.name': ..., 'service.version': '0.1.0'}
```

## 根因

`RuntimeMetricContract.otel_sdk_resource()` 定义的是项目自己的 canonical、进程级 Resource Contract，只包含 `service.name` 与 `service.version`。OpenTelemetry SDK 的 `MeterProvider` 在构造/导出 Resource 时还会携带 SDK 自身的标准 Resource 属性，例如 `telemetry.sdk.*`。这些属性属于 SDK 元数据，不属于项目 Runtime Metric Contract，因此 Real Acceptance 将 SDK 最终 Resource 与 canonical Resource 做完全字典相等比较是不正确的。

这不是 RuntimeTelemetry 业务指标、tenant boundary 或 canonical metric name 漂移，也不应通过向 Contract 中加入 SDK 版本等运行时元数据来修复；否则会把第三方 SDK 实现细节错误提升为业务 Contract。

## 修复

将 Real Acceptance 调整为：

1. canonical Resource 中的每个键值必须在 SDK 最终 Resource 中保持一致；
2. `tenant.id` 不得进入共享 MeterProvider Resource；
3. tenant 继续只通过 Metric observation 的 `tenant_id` 业务维度传递；
4. SDK 自动增加的 `telemetry.sdk.*` 元数据允许存在，但不进入项目 canonical Contract。

## 边界验证

该修复保持以下设计不变：

- Prometheus / OTLP 仍由 `RuntimeMetricContract` 统一定义；
- OpenTelemetry SDK 指标名仍直接复用 canonical metric names；
- 多租户不会共享 tenant Resource；
- 不新增第二套指标命名或 Resource Contract。

## 验证要求

代码提交后必须由开发者在本地执行：

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
```

随后在 Scheduler、Worker、PostgreSQL、Redis、API 均已由开发环境预先启动时执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\phase-2.10\03_alert_notification_lifecycle_real_gate.ps1
```

Gate 不自动启动、重启或停止任何服务，也不要求手工填写测试数据。
