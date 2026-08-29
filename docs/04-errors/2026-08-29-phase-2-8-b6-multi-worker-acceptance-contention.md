# Phase 2.8 B6 多 Worker 验收固定轮次误判

## 1. 发生时间

2026-08-29

## 2. 现象

开发者基于 `66c2edc6` 执行 `scripts/test/phase-2.8/06_delegation_multi_worker_runtime_gate.ps1`，前置步骤全部通过：

- B6 targeted Unit/Contract：37 passed；
- Backend default regression：869 passed, 3 skipped, 52 deselected；
- Alembic：`0039_workflow_node_execution_tenant_trigger (head)`；
- Real API：4 个测试中 3 个通过，B6 多 Worker 测试在 10 秒终态等待窗口超时。

失败测试：

`tests/api_real/test_agent_delegation_multi_worker_api.py::test_delegation_is_consumed_by_multiple_worker_instances_through_durable_frontier`

异常：

```text
TimeoutError: Durable Worker 未在验收等待窗口内完成本次 Delegation 集合
```

## 3. 根因分析

本次失败不是 Target Agent Runtime、Delegation completion 或 PostgreSQL 持久化链路本身报错，而是 B6 验收测试使用固定两轮显式 Worker dispatch 与并发 Claim 竞争组合产生的测试时序缺陷。

`_claim_pending_delegation_frontier()` 内部调用 `claim_delegation()`；后者在 Claim 成功后提交事务并释放 Delegation 候选行锁。两个 Worker 并发启动时，可能先从同一候选快照竞争：一个 Worker 成功 Claim，另一个 Worker 在随后进入 `claim_delegation()` 时收到 409 并返回 `None`。因此“一轮两 Worker 调用”不保证恰好消费两个不同 Delegation。

原测试固定执行两轮，隐含了“每轮两个 Worker 都必须各成功 Claim 一个任务”的错误假设。合法的 Claim contention 会导致部分 Delegation 仍保持 pending；随后测试没有继续调用显式 Worker dispatch，而直接等待终态，最终在 10 秒窗口结束时超时。

这不是通过增加业务 timeout 隐藏问题，也不是需要启动 Scheduler 的后台异步任务；验收测试本身必须在有界窗口内持续 drain 尚未消费的 Delegation。

## 4. 修复

将 B6 Real API 验收从固定两轮改为有界 drain：

1. 每轮先读取本次测试创建的 Delegation durable status；
2. 未全部终态时，并发调用两个正式 `_claim_pending_delegation_frontier()`；
3. 对成功 Claim 的 Frontier 继续调用正式 `execute_frontier()`；
4. 当一轮发生合法 contention 导致两个 Worker 均暂时没有 Frontier 时短暂让出事件循环并继续下一轮；
5. 总窗口仍为 10 秒，不修改 Delegation 业务 timeout，不启动后台服务或 Scheduler；
6. 最终仍由 `_wait_for_delegations_terminal()` 做终态断言，并继续验证每个 Delegation 只有一个 Worker Execution / Frontier 事实且两个 Worker owner 都实际参与 Claim。

这样验收的是“多 Worker 在真实 PostgreSQL Claim contention 下最终 drain 全部 Delegation”的真实能力，而不是固定轮数下的偶然调度结果。

## 5. 状态

**测试修复已提交，等待开发者本地重新执行 B6 Real Gate。**

在新的本地结果返回前，不将 Phase 2.8 标记为完成，也不提前进入 Phase 2.9。
