# 2026-08-27 DAG Decision Trace 事务边界缺口

`WorkflowRecoveryTraceLinkService.record_dag_decision()` 原实现无条件 `commit()`，会破坏 Runtime / Checkpoint / Frontier / Recovery Trace 的外层原子事务。

## 影响

可能出现 Decision Trace 已提交，但 Frontier 或 Checkpoint 随后回滚，造成审计事实与 durable progression 不一致。

## 修复

增加 `commit` 参数：默认 `True` 保持直接调用兼容；Durable Runtime / Recovery 可传入 `False`，此时只 `flush`，由外层事务统一提交。已存在 Decision Trace 的幂等命中仍只执行一致性校验。

## 验证

Unit Test 覆盖 `commit=False`、默认提交、Checkpoint lineage 与 Trace 幂等命中。完整 Regression / Real API / E2E 本轮不执行，也不记录为通过。
