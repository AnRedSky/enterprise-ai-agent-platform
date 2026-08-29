# 2026-08-29 Phase 2.10-I Notification 生命周期终态语义与幂等边界

## 现象

Runtime Notification 已经能够由 `WebhookDeliveryWorker` 回写 `delivered/retrying/failed/dead_letter`，但原实现存在两个运行时边界风险：

1. `failed` 可能被当成终态处理并提前触发 Provider fallback；实际上 Worker 在该状态下仍可能依据 retry policy 再次执行。
2. Notification dedup key 只由 instance、transition、group、destination 构成。同一告警实例 recovery 后再次 firing，若仍处于同一 grouping window，可能复用同一 key；并发路由也可能产生重复插入竞争。

## 根因

Notification Runtime 同时承担生命周期事实与 Provider attempt 事实。Provider retry 属于单次 Webhook Delivery 的内部状态，只有 `dead_letter` 才代表当前 Provider tier 已经耗尽重试预算；fallback 必须发生在该终态之后。

Grouping 是跨多个 lifecycle transition 的聚合边界，因此 group id 本身不能作为一次通知的唯一身份。需要把 `fire_count` 与 Provider tier 一并纳入稳定幂等键。

## 修复

- `AlertLifecycleService.record_delivery_outcome()` 只在 `dead_letter` 时触发 Provider fallback。
- `delivered/dead_letter` 终态重复回写直接幂等返回，不重复增加 attempt_count，不重复触发 fallback。
- Notification dedup key 增加 tenant、alert instance、fire_count、transition、group、destination、provider。
- Notification Delivery 使用 PostgreSQL `ON CONFLICT DO NOTHING`，把并发重复路由收敛为同一持久化事实。
- fallback exhausted 继续保留 `dead_letter` Notification 状态，并额外记录 `notification.fallback.exhausted` Audit 与 `notification.dlq` Metric。

## 验证边界

真实验收必须验证：

```text
Alert firing
  -> primary provider dead_letter
  -> fallback provider planned/delivered
  -> Notification audit/metrics
  -> recovery transition
  -> grouping + lifecycle dedup
  -> tenant isolation
```

测试 Gate 由 `03_alert_notification_lifecycle_real_gate.ps1` 自动启动并停止 Scheduler / Worker，测试数据自动创建和清理，不要求手工填写 tenant、destination 或 credential。
