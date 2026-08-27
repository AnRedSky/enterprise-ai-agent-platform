# Durable Frontier Replay Worker / Lifecycle Audit

## 日期

2026-08-27

## 阶段

Phase 2.7 Advanced Workflow Orchestration / Durable Recovery Closure

## 问题

Replay convergence 原实现把 Checkpoint 的 `worker_owner` 与当前 replay 调用者的 Worker owner 进行相等比较。Worker owner 属于短生命周期的 ownership / fencing 事实，不应成为已经提交 Durable completion fact 的跨 Worker Replay identity。

同时，Replay 已经找到 completion Checkpoint 后没有再次核对当前 `WorkflowExecution.status`，因此存在 Checkpoint lifecycle 与当前 Execution lifecycle 分叉时仍尝试收敛的风险。

## 修复

`backend/app/services/workflow/frontier_progression.py`：

1. Replay payload binding 不再把 ephemeral `worker_owner` 作为 Durable fact identity；仍严格比较 `state_data`、source Frontier、Workflow Execution、Workflow Version、Next Frontier、decision fingerprint 与 Node-set。
2. 找到唯一 completion Checkpoint 后重新读取关联 Execution。
3. 强制 `checkpoint.execution_status == execution.status`，发现 lifecycle drift 时 fail-closed。
4. Execution 不存在时拒绝 Replay convergence。

## 不变量

```text
Worker owner
    = ownership / fencing metadata
    ≠ Replay identity

Replay identity
    = source Frontier
    + completion Checkpoint
    + execution lifecycle
    + Next Frontier identity
    + decision fingerprint
    + Node-set
```

## Unit Test

新增：

```text
backend/tests/unit/test_frontier_replay_lifecycle_audit.py
```

覆盖：

- 新 Worker 可以重新收敛历史 completion fact；
- Checkpoint `execution_status` 与当前 Execution status 不一致时 fail-closed。

## 测试状态

本次仅新增 Unit Test 实现，未执行 pytest、集成测试、本地手动测试或 E2E。

## 结论

该修复继续推进 Replay convergence final audit，但不在本记录中提前宣布 Phase 2.7 完成；完成宣布必须等待 Success / Failure terminalization 与 Replay convergence 两项最终代码审计结束。