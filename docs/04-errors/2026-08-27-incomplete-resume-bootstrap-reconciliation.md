# 2026-08-27 — Incomplete Resume Bootstrap Reconciliation

## 1. 问题

Durable Resume 的幂等键可以已经创建 `WorkflowExecution`，但如果事务在 Resume Bootstrap 建立 completed Node lineage / Durable Frontier 前异常中断，后续 Recovery 会再次命中同一个 Resume。

原行为只能拒绝该幂等命中。这样虽然避免创建第二个 Resume，却会让一个仍处于 `pending`、没有 Worker ownership 的不完整 Resume 永久停留在“存在但不可消费”的状态。

## 2. 根因

Resume 的创建与 Bootstrap 已经要求处于同一事务，但历史异常、回滚恢复或未来边界变化仍可能留下需要重新协调的 pending Resume。单纯检查 Frontier 是否存在不足以完成生命周期收口。

## 3. 修复

`WorkflowExecutionResumeContractService` 现在把 Resume outcome 明确分为：

- `created`：首次创建 Resume 并完成 Bootstrap；
- `idempotency_hit`：已有完整 Resume 与 Durable Frontier；
- `reconciled`：已有合法 pending Resume，但缺少 Durable Frontier，由同一 Source Execution 锁内重新执行幂等 Bootstrap。

只有同时满足以下条件才允许自愈：

1. tenant / workflow / version / source / checkpoint lineage 全部一致；
2. Resume 仍为 `pending`；
3. Resume 尚未取得 Worker ownership；
4. Bootstrap 本身再次完成 Node lineage 与 Frontier Contract 校验。

已经运行或持有 Worker ownership 的不完整 Resume 不会被自动接管，直接拒绝，避免 Recovery Domain 与 Worker 并发争夺状态机所有权。

## 4. Scheduler 收口

Recovery Scan 新增 `reconciled` 计数，并将其作为成功恢复结果统计，避免 Scheduler 把合法自愈错误记录为 rejected。

## 5. 测试范围

新增 Unit Test 覆盖：

- pending + 无 Frontier → `reconciled`；
- reconciliation 不创建第二个 Resume；
- reconciliation 在当前事务内提交；
- 已持有 Worker ownership 的不完整 Resume → 拒绝。

当前暂停 Full Regression / Real API / E2E；未执行的测试不得记录为 PASS。
