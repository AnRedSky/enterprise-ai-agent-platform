# 2026-08-27 Durable Frontier Claim 层并发消费边界

## 1. 工程问题

`Next Frontier` 创建阶段已经能够拒绝同一 `WorkflowExecution` 下活动 Frontier 的 Node-set overlap，但如果 Worker Claim 层只依赖 `frontier_key` 唯一约束，则不同 `decision_fingerprint` / identity 的 Frontier 仍可能同时进入 Claim。

示例：

```text
Frontier A: [node-a, node-b]
Frontier B: [node-b, node-c]
```

两个 Frontier 的 `frontier_key` 可以不同，但都可能消费 `node-b`。如果 Claim 层没有再次证明同一 Execution 的活动 Node 集合互斥，Runtime 才发现冲突已经太晚。

## 2. 根因

原 Claim 路径只锁定候选 Frontier，并通过关联 Execution 的 owner / lease 条件判断是否可消费；没有把同一 Execution 的活动 Frontier Node-set 作为 Claim contract 的一部分。

此外，直接采用 `Execution → Frontier` 的反向锁顺序会与 terminalization 当前使用的 `Frontier → Execution` 顺序形成潜在死锁，因此 Claim 必须保持既有锁顺序。

## 3. 修复

`backend/app/services/workflow/frontier_repository.py` 的 `claim_next_frontier()` 现在：

1. 先按既有 Claim 路径锁定候选 Frontier；
2. 使用 `skip_locked` 锁定关联 Execution，避免不同 Frontier 各自持有 Frontier lock 后互相等待 Execution lock；
3. Execution 锁成功后重新证明 Execution 状态与 owner / lease eligibility；
4. 在同一事务内检查同 Execution 的其他活动 Frontier Node-set；
5. 发现 overlap 时拒绝本次 Claim，由上层 rollback 后等待后续调度；
6. 只有 Node-set 互斥时才写入 `claimed / worker_owner / lease / attempt`。

活动 Frontier 查询不再额外锁其他 Frontier，避免与 terminalization 的 `Frontier → Execution` 锁顺序产生反向等待。对于正在 terminalization 的并发事务，若可见状态仍属于活动 Frontier，本次 Claim 采用保守拒绝策略，下一轮重新竞争。

## 4. 单元测试

新增：

`backend/tests/unit/test_frontier_claim_fencing.py`

覆盖：

- Claim 时同 Execution 活动 Frontier Node-set overlap → 不进入 claimed；
- disjoint parallel Frontier → 正常进入 claimed；
- Execution lock 不可取得 → 不消费候选 Frontier。

本轮没有执行 pytest，因此测试结果不标记为 PASS。

## 5. 后续边界

Claim-layer overlap fencing 已完成，但 Phase 2.7 仍需继续完成：

```text
Worker Claim 同 Execution 并发边界
        ↓
Success / Failure terminalization closure
        ↓
Replay convergence
        ↓
Phase 2.7 主线完成
```

在全部主线完成前继续暂停完整测试、Real API、E2E 和本地手动验收。