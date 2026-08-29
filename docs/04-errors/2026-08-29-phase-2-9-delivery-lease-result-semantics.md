# 2026-08-29 Phase 2.9-C 投递服务租约丢失返回值语义

## 1. 现象

`IntegrationEventDeliveryService.deliver_once()` 在 Sender 执行完成后，即使 `mark_delivered()` 因租约已经被其他 Worker 接管而返回 `False`，原实现仍然固定返回 `True`。

同样的问题也存在于 Sender 失败后的 `mark_failed()` 路径。

## 2. 根因

Repository 已经通过 `lease_owner` 条件实现旧 Worker fencing：状态更新找不到当前租约时返回 `False`。Delivery Service 没有向上透传这个结果，而是把“进入发送处理流程”错误地等同于“本 Worker 成功完成状态提交”。

这会让上层 Worker 将已经失去租约的旧任务误判为成功处理，破坏 Durable Delivery 的并发控制语义。

## 3. 修复

`deliver_once()` 现在直接返回 `mark_delivered()` / `mark_failed()` 的布尔结果：

- `True`：当前 Worker 成功完成最终状态更新；
- `False`：没有可领取事件，或当前 Worker 已失去租约。

Sender 异常仍由 Delivery Service 转换为 retry / dead-letter 状态，不向 Worker 泄漏外部发送异常；只有最终状态写入是否仍属于当前租约由返回值表达。

## 4. 防回归

新增单元测试覆盖“发送完成但租约已丢失”场景，并新增真实 PostgreSQL 验收覆盖：

- 并发 Claim 只有一个租约持有者；
- 租约过期后可被新 Worker 恢复；
- 旧 Worker 无法覆盖新 Worker 的最终状态；
- tenant isolation；
- retry → dead-letter 状态机。

真实 PostgreSQL Gate：

```text
backend/scripts/test/phase-2.9/01_reliable_delivery_postgres_gate.ps1
```

## 5. 验收边界

本次修复不能在未执行开发者本地 PostgreSQL Real Gate 前标记 2.9-C 第二切片完成。Gate 不启动、不停止任何服务；测试数据自动生成并清理。
