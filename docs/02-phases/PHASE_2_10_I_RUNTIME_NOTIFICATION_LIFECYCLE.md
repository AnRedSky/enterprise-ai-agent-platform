# Phase 2.10-I Runtime Notification Lifecycle

## 目标

在已有 Event / Delivery / Replay / Provider / Metrics / Alert 基础能力之上，完成告警通知运行时闭环，不重复建设底层 Delivery。

```text
Alert Evaluation
    ↓
Alert Firing / Recovery
    ↓
Notification Policy
    ↓
Grouping / Dedup / Cooldown
    ↓
Provider Routing
    ↓
WebhookDeliveryWorker
    ↓
Notification Delivery Outcome
    ↓
Fallback / Retry / DLQ
    ↓
SLO / Metrics
    ↓
Operational Audit
```

## 本切片实现

### 1. Alert 生命周期

- `AlertLifecycleService` 负责 firing / recovery 状态转换；
- 只有真正发生 transition 才生成通知事实；
- `fire_count` 用于区分同一告警实例跨 recovery 后的新一轮 firing；
- severity、routing key、escalation 在 transition 时固化。

### 2. Notification Policy / Group / Cooldown

- Policy 按 tenant + severity + routing key 选择；
- group 在配置窗口内复用，跨窗口自动形成新 group；
- firing 受 `next_notification_at` cooldown 约束；recovery 不被 firing cooldown 错误抑制；
- Notification dedup key 包含 tenant、alert instance、fire_count、transition、group、destination、provider。

### 3. Provider Routing / Fallback

- Provider order 继续复用已有 `AlertNotificationDeliveryService`；
- Worker `retrying/failed` 不触发 fallback；
- 只有当前 Provider `dead_letter` 后才选择下一 Provider tier；
- fallback exhausted 保持 Notification `dead_letter`，并写入 `notification.fallback.exhausted` Audit 与 `notification.dlq` Metric。

### 4. Worker Outcome

`WebhookDeliveryWorker` 已通过 `AlertLifecycleService.record_delivery_outcome()` 回写 Notification Delivery：

- delivered
- retrying
- failed
- dead_letter

终态重复回写幂等，不重复增加 attempt_count 或触发 fallback。

### 5. Scheduler 边界

`alert.*` Integration Event 已由 AlertLifecycleService 按 Notification Policy 独占路由。

通用 `NotificationDispatcher` 与 `RuntimeNotificationScheduler` 明确排除 `alert.*`，防止 Scheduler 绕过 Notification Policy 产生第二套告警通知路由。

### 6. Metrics / SLO / Audit

- Notification Delivery 状态持续写入 `RuntimeMetricSample`；
- Provider / transition / severity 等维度保留在 Metric dimensions；
- Runtime Operations 继续提供 Notification SLO 与 Alert 评估；
- Notification route / delivery / fallback / DLQ 均写入 Runtime Operational Audit。

## 自动化验收

入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\03_alert_notification_lifecycle_real_gate.ps1
```

Gate 自动：

1. 检查 Alembic heads 并执行 `upgrade heads`；
2. 启动 Scheduler Service；
3. 启动 Webhook Worker；
4. 创建 loopback HTTP receiver；
5. 自动创建 tenant / rule / policy / destination / subscription；
6. 验证 primary failure → dead letter → fallback → delivered；
7. 验证 recovery、grouping、lifecycle dedup、SLO、Metrics、Audit、tenant isolation；
8. 自动清理全部验收数据；
9. 无需手工填写测试信息。

## 当前状态

**代码实现完成，Real PostgreSQL Acceptance 待本地执行结果收口。**

Git 提交：

- `0c625381`：harden runtime notification lifecycle；
- `9fda9be5`：isolate alert routing from generic notification scheduler。
