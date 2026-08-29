# Phase 2.9-D Webhook Real Acceptance：跨租户 Claim 导致目标 Delivery 未更新

## 1. 现象

Phase 2.9-E Runtime Integration Real Gate 的 Webhook handoff 在真实 PostgreSQL + HTTP Acceptance 阶段失败：

```text
1 passed in 0.33s
24 passed in 0.91s

AssertionError: assert 'pending' == 'delivered'
```

测试创建的 Delivery 保持 `pending`，但 `WebhookDeliveryWorker.deliver_once()` 返回 `True`。

## 2. 根因

`WebhookDeliveryWorker.deliver_once()` 的语义是“领取一个可投递 Delivery”。原实现调用 `WebhookDeliveryRepository.claim_next()` 时没有任何 tenant predicate。Repository 因此可以从数据库中领取任意租户的最早可投递 Delivery。

Real Acceptance 本身会自动生成唯一 tenant 和 delivery，并要求本次 `deliver_once()` 完成该 fixture 的 HTTP 投递。如果本地 PostgreSQL 中存在上一轮失败、残留或其他租户的 pending Delivery，Worker 可能合法地领取另一个 Delivery 并返回 `True`，随后 Acceptance 查询自己的 delivery 时仍然得到 `pending`。

这不是 HTTP Provider 或 PostgreSQL 状态更新失败，而是 Acceptance 可确定性与 Worker 租户边界之间的缺失。

## 3. 修复

为 `WebhookDeliveryRepository.claim_next()` 增加可选 `tenant_id` predicate；为 `WebhookDeliveryWorker` 增加可选 `tenant_id`。

- 默认 `tenant_id=None`：保持平台级 Worker 全局消费行为，适用于正式多租户 Worker。
- 指定 `tenant_id`：Worker 只 Claim 指定租户的 Delivery Fact，适用于 tenant-scoped Worker pool 与确定性 Acceptance。
- Phase 2.9-D Real Acceptance 使用生成的 `tenant_id` 初始化 Worker，避免其他租户的本地 Delivery 干扰目标 fixture。

## 4. 设计原则

1. 不通过删除其他租户数据来“修复” Acceptance。
2. 不修改 `mark_delivered()` 来掩盖错误 Claim。
3. 不把目标 delivery_id 硬编码到生产 Worker。
4. 保留平台级 Worker 的跨租户消费能力。
5. Tenant-scoped Worker 是显式运行配置，不改变默认行为。

## 5. 变更文件

- `backend/app/services/integration/webhook_delivery_repository.py`
- `backend/app/services/integration/webhook_delivery.py`
- `backend/tests/api_real/test_webhook_delivery_acceptance.py`

## 6. 验证要求

重新执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\phase-2.9\02_webhook_delivery_real_gate.ps1
```

随后由 `03_runtime_integration_real_gate.ps1` 统一验证 Runtime Integration + Webhook Real Acceptance。

本文件只记录失败根因与修复，不预填 Acceptance 通过结果。
