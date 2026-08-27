# Durable Frontier Terminal Replay Lifecycle Closure

- 日期：2026-08-27
- 阶段：Phase 2.7 Advanced Workflow Orchestration
- 状态：已实现，测试暂缓

## 问题

已有 `frontier_completed` Replay binding 已经验证 source Frontier、Checkpoint payload、Execution、Workflow Version、decision fingerprint 与 Node-set，但仍存在一个 lifecycle 形态缺口：

- 第一次 completion 产生 `execution_status=running`，说明存在 Next Frontier；
- Replay 调用如果省略 `next_identity`，原实现可能把同一个 Durable completion 错误收敛成“无 Next Frontier”的另一种生命周期结果；
- 反向地，第一次 completion 已经 `execution_status=completed` 时，Replay 不应通过追加 `next_identity` 改变 terminal lifecycle。

这不是新的 Frontier identity 冲突，而是 Replay 对第一次 terminalization lifecycle 的语义漂移。

## 修复

在 `backend/app/services/workflow/frontier_progression.py` 的 `_resolve_completed_frontier_idempotency()` 中增加 lifecycle binding：

```text
existing completion checkpoint
        ↓
execution_status == running
        ├── next_identity missing → reject
        └── next_identity present → continue exact binding checks

execution_status == completed
        ├── next_identity present → reject
        └── next_identity absent → terminal replay allowed

other status
        → reject
```

因此 Replay 必须复现第一次 completion 的 lifecycle 形态，而不是只证明 payload 相同。

## 单元测试

新增：

`backend/tests/unit/test_frontier_terminal_replay_lifecycle.py`

覆盖：

1. running completion 缺少 Next Frontier identity 时拒绝；
2. completed terminalization 追加 Next Frontier identity 时拒绝。

## 测试状态

本轮未执行 pytest、集成测试、Real API、Browser E2E 或本地手动测试。仅提交 Unit Test 实现，不记录 PASS。
