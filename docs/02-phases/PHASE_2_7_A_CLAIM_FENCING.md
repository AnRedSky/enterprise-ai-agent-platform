# Phase 2.7-A Claim-layer Fencing Delivery Record

> 状态：**已完成**。
> 基线：`main`，2026-08-27。
> 所属阶段：Phase 2.7 Advanced Workflow Orchestration / Durable Recovery Closure。

## 1. 交付目标

补齐 Durable Frontier Worker Claim 层的同一 Execution 并发边界，使 Claim 不仅证明 Frontier identity / Execution ownership 可消费，还必须证明活动 Frontier 的 Node 集合不会重复消费。

## 2. 实际实现

`backend/app/services/workflow/frontier_repository.py` 的 `claim_next_frontier()` 已完成：

- 保留候选 Frontier → Execution 的锁顺序，避免与 terminalization 的 Frontier → Execution 锁顺序形成反向死锁；
- 关联 Execution 使用 `skip_locked`，Execution 已被其他并发 Claim 占用时，本次 Claim 不修改候选 Frontier；
- Execution 锁定后重新证明 `pending/running` 状态与当前 Worker owner / lease eligibility；
- Claim 前检查同一 Execution 的 `pending/retry_wait/claimed/running` Frontier Node-set；
- Node-set overlap 时拒绝进入 `claimed`，不递增 attempt，不写 owner / lease；
- disjoint parallel Frontier 正常进入 `claimed`；
- 活动 Frontier 查询不额外锁其他 Frontier，避免形成 `Execution → Frontier` 与 terminalization `Frontier → Execution` 的锁循环；
- 发生并发 terminalization 时采用保守拒绝并等待下一轮 Claim，而不是放行潜在重复消费。

## 3. 单元测试实现

新增：

`backend/tests/unit/test_frontier_claim_fencing.py`

覆盖：

1. 同一 Execution 的活动 Frontier Node-set overlap；
2. 同一 Execution 的 disjoint parallel Frontier；
3. Execution lock 不可取得时不消费候选 Frontier。

本轮**未执行 pytest**，因此没有测试 PASS 结论。

## 4. 工程错误记录

详细记录：

`docs/04-errors/2026-08-27-durable-frontier-claim-overlap-fencing.md`

该记录描述了原 Claim contract 只依赖 Frontier identity / Execution eligibility、无法证明不同 fingerprint 的重叠 Node-set，以及锁顺序设计约束。

## 5. 当前边界

Claim-layer Duplicate Consumption Guard 已完成，但 Phase 2.7 尚未完成。下一主线为：

```text
Success / Failure terminalization closure
        ↓
Replay convergence
        ↓
Phase 2.7 主线完成
```

在主线全部完成前继续暂停完整测试、Real API、E2E 与本地手动验收。