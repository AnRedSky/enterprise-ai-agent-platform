# 2026-08-27 — Recovery 多 Frontier 重入导致 pending Execution 阻塞

## 问题

Recovery 可以在同一个 Workflow Execution 下同时把多个已过期 Frontier 放回 `retry_wait`。Recovery 之前已经保证 Frontier lease 与 Execution lease 同时失效，但 Claim 在重新取得 Execution ownership 后，会把 `running` Execution 设置为 `pending`。

如果同一 Execution 仍有第二个 `retry_wait` Frontier，旧 Claim predicate 会把 `pending + 当前 Worker owner` 视为不可消费，导致后续 Frontier 无法再次 Claim。

典型场景：

```text
Execution E
 ├── Frontier F1  expired
 └── Frontier F2  expired

Recovery
 ├── F1 → retry_wait
 └── F2 → retry_wait

Worker B Claim F1
 └── E → pending + owner=B

Worker B Claim F2
 └── 旧 predicate：pending + owner=B → reject
```

## 根因

`WorkflowExecution.status=pending` 同时用于“尚未取得 Worker ownership”和“Recovery 后由当前 Worker 持有、等待继续消费 Frontier”的过渡状态。Claim candidate predicate 与最终 Claim branch 没有覆盖第二种情况。

## 修复

统一允许：

```text
pending
AND
(worker_owner IS NULL OR lease expired OR worker_owner == current_worker)
```

当 `pending` Execution 已由当前 Worker 持有时：

- 复用当前 `worker_attempt` / fencing generation；
- 只刷新 Execution lease；
- 不递增 generation；
- 后续 Frontier 可以继续 Claim；
- 不改变 terminalization 所需的 Worker epoch 语义。

`_frontier_tenant_candidate()` 与 `claim_next_frontier()` 使用相同 eligibility，避免 candidate 查询与最终 Claim 再次分裂。

## 安全边界

仍然拒绝：

- 其他 Worker 持有有效 Execution lease；
- completed / failed / cancelled Execution；
- ownership / fencing generation 不匹配；
- Frontier 不属于当前 tenant / Execution lineage。

## 测试

新增 `backend/tests/unit/test_frontier_recovery_reentry.py`，覆盖当前 Worker 持有 pending Execution 时的 candidate / claim Contract，以及 Recovery 不隐式清除 Execution ownership。

按项目当前开发策略，本轮未执行 pytest；测试结果不得记录为 PASS。
