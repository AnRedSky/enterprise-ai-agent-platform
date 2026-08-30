# Runtime Notification Outcome 跨租户查询边界缺失

## 发现
Phase 2.10-I Runtime Notification Worker 在同步 Webhook Delivery outcome 时，原 `AlertLifecycleService.record_delivery_outcome()` 仅使用 `webhook_delivery_id` 查询 `RuntimeNotificationDelivery`，没有同时约束 `tenant_id`。

## 根因
Worker 已经从 `WebhookDelivery` Claim 事实获得所属租户，但结果同步接口没有继续传递该安全边界，导致同一 Delivery ID 被错误传入时，查询语义缺少 tenant predicate。

## 修复
- `record_delivery_outcome()` 增加必填 `tenant_id` 参数；
- 查询同时使用 `tenant_id + webhook_delivery_id`；
- `WebhookDeliveryWorker` 从已 Claim 的 Delivery Fact 读取 `record.tenant_id` 并传递到 outcome sync；
- 增加单元测试验证生成的 SQL 同时包含两个边界条件。

## 边界
该修复不改变 Notification 状态机、Retry、Dead Letter 或 Fallback 规则，只补齐结果同步阶段的 tenant authorization boundary。

## 验证
开发者本地应执行 targeted unit tests、Backend default regression，以及 Phase 2.10-I Real Acceptance Gate。当前提交仅记录代码变更，未声称尚未执行的本地测试结果。
