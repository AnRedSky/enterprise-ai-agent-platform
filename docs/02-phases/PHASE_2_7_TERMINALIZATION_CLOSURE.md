# Phase 2.7 — Terminalization / Replay Closure

> 状态：**开发中**。
> 基线：`main`，2026-08-27。
> 所属阶段：Phase 2.7 Advanced Workflow Orchestration / Durable Recovery Closure。
> 主阶段文档：`docs/02-phases/PHASE_2_7.md`。

## 1. 当前目标

在 Durable Frontier Claim、Runtime Consumption、Checkpoint fencing、Recovery、Success / Failure convergence 已建立的基础上，继续收口终态一致性与 Replay convergence。

目标不是新增第二套 Workflow Runtime 或 Planner，而是保证同一 Durable fact 在重复 completion、retry、recovery、stale Worker 与 replay 场景下只能收敛到一个合法结果。

## 2. 已完成

### 2.1 Claim 层并发 fencing

- 同一 Execution 的活动 Frontier Node-set overlap 在 Claim 前拒绝；
- disjoint parallel Frontier 仍允许并行；
- Claim 保持 `Frontier → Execution` 锁顺序，避免与 terminalization 形成交叉锁序。

### 2.2 Progression 层并发 fencing

- Next Frontier 创建前检查同 Execution 活动 Frontier Node-set；
- overlap 在 durable progression transaction 内直接拒绝；
- 不依赖 Runtime 内存状态或 NodeExecution 唯一约束作为重复消费兜底；
- sibling overlap 检查只做一致性读取，不在已持有 Execution 锁后再次锁 sibling Frontier，避免引入反向锁序。

### 2.3 Terminalization lock-order

- Planner Runtime 成功路径不再提前锁定 Execution；
- 最终 progression 统一按 `Frontier → Execution` 顺序获取锁；
- Failure convergence 使用相同锁序；
- Runtime snapshot 只负责执行读取，最终 durable write 重新执行 ownership / lease / lifecycle fencing。

### 2.4 Terminal Replay Binding

`complete_frontier_with_checkpoint()` 的重复 completion 已增加严格 Replay binding：

```text
source Frontier
      ↓
frontier_completed Checkpoint
      ↓
既有 Next Frontier
      ├── same Execution
      ├── same Workflow Version
      ├── same decision fingerprint
      └── same Node set
```

任一条件 drift 都必须拒绝 Replay convergence，不允许产生第二套 durable fact。

### 2.5 Terminal Replay Lifecycle

- `running` completion 必须继续提供原始 Next Frontier identity；
- `completed` terminalization 禁止追加 Next Frontier identity；
- Replay 不得通过省略或伪造 `next_identity` 改变 Execution lifecycle。

### 2.6 Success / Failure sibling closure

- Success terminalization 前禁止同一 Execution 存在仍可消费的 sibling Frontier；
- Failure terminalization 时，同一事务关闭仍处于 `pending / retry_wait / claimed / running` 的 sibling Frontier；
- terminal Execution 不再与可消费 Durable work item 并存。

### 2.7 Duplicate completion Durable fact closure

- 同一 source Frontier + completion reason 的 completion Checkpoint 必须唯一；
- 发现多个 completion Checkpoint 时 fail-closed；
- Replay 不得通过 `ORDER BY sequence DESC LIMIT 1` 猜测权威 Durable fact。

### 2.8 Replay worker / lifecycle independence audit

- Replay 不再把 ephemeral `worker_owner` 当作 Durable identity；
- Replay 可以由新的 Worker 收敛已经提交的 completion fact；
- Replay 找到唯一 completion Checkpoint 后必须重新读取关联 Execution；
- Checkpoint `execution_status` 必须与当前 Execution lifecycle 一致，否则 fail-closed；
- Execution 缺失时拒绝 Replay convergence。

### 2.9 Checkpoint writer Replay ownership independence

- `frontier_completed` Checkpoint 的重复写入幂等边界只比较 Durable completion fact，不比较历史 `worker_owner`；
- 新 Worker Replay 同一 completion fact 时不得因为 ephemeral owner 变化而追加第二条 Checkpoint；
- `worker_owner / worker_attempt / lease` 继续只用于当前实时写入的 fencing，而不成为历史 Replay identity。

## 3. 当前终态模型

```text
Worker Runtime
     ↓
Success / Failure
     ↓
Frontier lock
     ↓
Execution lock
     ↓
Ownership + lease + lifecycle fencing
     ↓
Checkpoint / Frontier / Execution progression
     ↓
Replay binding
     ├── source Frontier
     ├── fingerprint
     ├── Node-set
     ├── Checkpoint payload
     └── lifecycle
     ↓
Durable fact uniqueness
     ↓
COMMIT / ROLLBACK
```

## 4. 当前主线最终审计

### 4.1 Success / Failure terminalization final audit

逐项证明：

- completed / failed / cancelled Execution 不会重新生成可消费 Frontier；
- retry budget exhausted 时 Frontier 与 Execution 在同一补偿事务内进入 failed；
- 已 terminalize 的 Execution 不允许旧 Frontier Recovery re-entry；
- duplicate success 与 duplicate failure 不产生第二套 terminal fact；
- failure path 不会覆盖其他 Worker 已取得的 Execution ownership；
- stale Worker 不会通过异常收敛改变已经转移的 Execution lifecycle；
- success / failure 与 sibling Frontier 的锁序不存在反向等待窗口；
- terminalization 后 Frontier、Checkpoint、Execution 生命周期保持一致。

### 4.2 Replay convergence final audit

继续验证：

```text
same source Frontier
      + same durable completed facts
      ↓
same decision fingerprint
      ↓
same Frontier identity
      ↓
same Checkpoint binding
      ↓
same Checkpoint payload
      ↓
same lifecycle
      ↓
same terminal result
```

不得通过更换 fingerprint、Node-set、Checkpoint payload、Next Frontier identity 或 lifecycle 形态绕过幂等边界。

同时必须满足：

```text
worker_owner
    = transient ownership / fencing metadata
    ≠ replay identity
```

Replay 的最终一致性必须由 Durable facts 本身证明，而不是由“当前 Worker 恰好与历史 Worker 相同”证明。

### 4.3 Checkpoint writer / Replay symmetry audit

最终需要确认两条路径对同一 `frontier_completed` Durable fact 使用完全一致的 identity：

```text
Original completion
    ↓
append_next_in_transaction()
    ↓
(frontier_id, reason, execution, payload, lifecycle)

Replay completion
    ↓
append_next_in_transaction()
    ↓
同一 Durable identity
    ↓
返回既有 Checkpoint
```

禁止出现：

```text
Original path identity
    !=
Replay path identity
```

导致“原始提交只有一条、Replay 又追加一条”的情况。

## 5. 单元测试

已补充 / 调整 Unit Test：

```text
backend/tests/unit/test_frontier_duplicate_consumption.py
backend/tests/unit/test_frontier_terminal_replay_lifecycle.py
backend/tests/unit/test_frontier_terminalization_sibling_guard.py
backend/tests/unit/test_frontier_failure_terminalization.py
backend/tests/unit/test_frontier_lock_order.py
backend/tests/unit/test_frontier_replay_lifecycle_audit.py
backend/tests/unit/test_checkpoint_replay_worker_independence.py
```

当前 Unit Test 仅作为生产主线的断言实现，不提前执行完整测试 Gate。

## 6. 测试状态

本轮仍未执行：

- `pytest`；
- Backend Full Regression；
- Alembic migration verification；
- Frontend Gate；
- Real API；
- Browser E2E；
- 本地手动测试。

禁止将上述未执行项目记录为 PASS。

## 7. 下一任务

```text
Claim / overlap fencing                    ✅
Terminalization lock-order                 ✅
Terminal Replay Binding                    ✅
Terminal Replay Lifecycle                  ✅
Success / Failure sibling closure          ✅
Duplicate completion fact closure          ✅
Replay worker/lifecycle independence       ✅
Checkpoint writer Replay independence      ✅ 本轮
        ↓
Success / Failure terminalization final audit
        ↓
Replay convergence final audit
        ↓
Checkpoint writer / Replay symmetry audit
        ↓
Phase 2.7 主线完成
        ↓
进入完整本地自动化测试与手动验收
```

只有完成上述生产主线后，才启动用户要求的完整自动化测试脚本、环境准备、数据库 Migration、Backend Gate、Frontend Gate、Real API、E2E 与手动测试流程，并把实际执行结果写入 Acceptance 文档。