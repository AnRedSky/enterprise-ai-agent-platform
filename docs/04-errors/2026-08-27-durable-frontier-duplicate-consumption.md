# Durable Frontier 并行 Node 重叠消费边界

## 发现时间

2026-08-27

## 影响范围

Phase 2.7 Durable Frontier / Recovery / Replay Closure。

## 工程风险

同一 Workflow Execution 允许多个并行 Frontier 存在。`tenant_id + frontier_key` 唯一约束只能阻止完全相同 identity 的重复 Frontier，不能单独证明两个不同 fingerprint 的 Frontier 不会携带重叠的 Node 集合。

如果重复 Frontier 在不同 Worker / Recovery 时序下同时进入可消费状态，可能导致同一个 `WorkflowNodeExecution` 被多个 Frontier 消费。当前 `WorkflowNodeExecution(execution_id, node_id)` 唯一约束只能在节点 durable fact 写入时兜底，不能替代 Worker 消费边界，因为 Runtime 已经可能执行外部副作用。

## 修复策略

在既有 Frontier → Checkpoint → Next Frontier 单事务 progression 内增加集合级 fencing：

1. 锁定同一 tenant / execution 下除当前 Frontier 外的所有活动 Frontier；
2. 将 Next Frontier 的 `node_ids` 与其他 `pending / retry_wait / claimed / running` Frontier 的 Node 集合比较；
3. 发现重叠立即拒绝 progression；
4. 只有 Node 集合互斥时才创建 Next Frontier。

该规则不禁止合法的并行 Frontier，只禁止两个并行 work item 消费同一个 Node。

## 当前边界

本轮完成的是 **Next Frontier 创建前的 duplicate-consumption guard**。Worker Claim 层仍需要继续收口为“Claim + Execution ownership + 同 Execution Frontier overlap”统一事务边界；完成后才能将 Concurrent multi-frontier Claim 主线整体标记完成。

## 测试

新增单元测试覆盖：

- Next Frontier 与活动 Frontier Node 集合重叠时拒绝创建；
- Node 集合互斥时允许合法并行 Frontier。

本轮未执行 pytest；测试代码已提交但没有记录 PASS。
