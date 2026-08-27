# 2026-08-27 Durable Frontier failure convergence 跨层 ownership 风险

## 类型

代码审查发现的并发一致性风险；未执行本地运行测试，不将其描述为运行时已发生事故。

## 问题

Durable Frontier 的成功 terminalization 已经在 `complete_frontier_with_checkpoint()` 中先锁定关联 `WorkflowExecution`，并验证 Execution owner、worker epoch 与有效 lease。但异常路径 `_converge_failure()` 原先虽然分别锁定 Frontier 与 Execution，却在 `transition_owned_frontier()` 后直接执行 Execution failure terminalization。

这会留下一个跨层并发窗口：旧 Worker 仍持有 Frontier owner，而关联 Execution ownership 已经转移到其他 Worker 时，旧 Worker 可能先成功推进 Frontier failure，再把已经属于新 Worker 的 Execution 错误收敛为 `failed`。该路径与成功 terminalization 的 fencing 规则不一致。

## 修复

在 failure retry / failed convergence 的任何持久化动作前，统一要求：

```text
Execution.worker_owner == current Worker owner
AND
Execution.worker_lease_expires_at IS NOT NULL
AND
Execution.worker_lease_expires_at > now
```

证明失败后立即 rollback，不执行 Frontier transition、retry scheduling 或 Execution terminalization。

## 单元测试覆盖

- Execution ownership 已转移时，failure convergence 不得推进 Frontier；
- Execution lease 已过期时，failure convergence 不得进入 retry / failed；
- 既有成功 terminalization ownership/fencing 测试继续保留。

## 验证状态

本轮按照项目当前开发策略暂停完整测试流程；仅新增/更新 Unit Test 实现，未在本地执行 pytest、Backend Regression、Real API 或 E2E，因此不得记录测试 PASS。
