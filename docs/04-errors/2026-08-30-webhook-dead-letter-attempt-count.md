# Webhook Delivery 尝试次数耗尽后未进入死信

## 1. 发现时间

2026-08-30

## 2. 影响范围

- `backend/app/services/integration/webhook_delivery.py`
- `backend/app/services/integration/webhook_delivery_repository.py`
- `backend/tests/api_real/test_alert_notification_runtime_acceptance.py`
- Phase 2.10-I Alert → Notification → Worker → Fallback Runtime 闭环

## 3. 现象

执行 Phase 2.10-I Runtime Notification Acceptance 时，Primary Webhook Delivery 配置 `max_attempts=1`，Provider 第一次投递失败后，验收实际观察到 Delivery 仍为 `pending`，而预期必须为 `dead_letter`。

## 4. 根因分析

原实现由 Worker 根据领取时记录的 `attempt_count` 预计算 `retry_at`，Repository 仅根据传入的 `retry_at is None` 决定 `dead_letter` 或 `pending`。这样会把重试耗尽判定依赖在 Worker 与 Repository 之间传递的派生值上，而真正可靠的状态事实是数据库中已持久化的累计 `attempt_count`。

Phase 2.10-I 的闭环要求 `max_attempts=1` 的第一次失败立即进入 `dead_letter`，随后由 Notification Runtime 触发 fallback routing。因此必须由持久化状态机在加锁后的记录上重新确认是否已经耗尽尝试次数。

## 5. 修复方案

`WebhookDeliveryRepository.mark_failed()` 新增 `max_attempts` 参数，并在行锁保护下使用持久化 `record.attempt_count >= max_attempts` 作为最终死信判定：

- 已耗尽：`dead_letter`，清空 `next_attempt_at`；
- 未耗尽：`pending`，保留 Worker 计算的下一次重试时间。

Worker 将自身的 `max_attempts` 显式传递给 Repository。这样即使 Worker 侧计算的 `retry_at` 与实际领取次数发生偏差，Repository 仍以数据库状态作为最终权威事实。

同时增加单元回归测试覆盖“尝试次数耗尽必须死信”和“未耗尽继续 pending”两个边界。

## 6. 回归要求

```powershell
cd backend
uv run pytest -q tests/unit/test_webhook_delivery_repository.py
uv run pytest -q -m real_api tests/api_real/test_alert_notification_runtime_acceptance.py --tb=short
uv run pytest -q
```

Phase 2.10-I Real Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\03_alert_notification_lifecycle_real_gate.ps1
```

Gate 不自动创建、启动、重启或停止 API、Worker、Scheduler、PostgreSQL、Redis；真实测试数据由 Acceptance 自动生成和清理。
