# 2026-08-27 Durable Frontier Duplicate Completion Convergence

## 1. 问题

Durable Frontier completion 已具备 Frontier fencing、Execution ownership recheck、Checkpoint lifecycle guard 和 deterministic Next Frontier identity，但此前对“同一个 completion 请求已经提交、旧 Worker/HTTP retry 再次提交”的处理仍然直接进入 `transition_owned_frontier()`。

第一次请求提交后：

```text
Frontier → completed
Checkpoint → frontier_completed
Next Frontier → existing/new
COMMIT
```

第二次相同请求再次执行时，当前 Frontier 已经是 `completed`，原 ownership transition 会直接失败。对于真正的重复请求，这会把一个已经成功完成的 durable operation 暴露成普通 fencing failure；更重要的是，如果调用方试图自行补偿，就可能产生第二条 completion fact。

## 2. 根因

幂等性只在 Next Frontier `enqueue_frontier()` 层存在，completion 本身缺少“已提交结果的重新读取与一致性证明”入口。

因此需要区分：

```text
第一次 completion
    ↓
执行状态推进 + Checkpoint + Next Frontier
    ↓
COMMIT

重复 completion
    ↓
读取已经完成的 Frontier
    ↓
读取既有 frontier_completed Checkpoint
    ↓
校验 payload / owner / Next Frontier identity
    ↓
返回既有 Durable facts
```

## 3. 修复

`complete_frontier_with_checkpoint()` 在真正执行 ownership transition 前增加 `_resolve_completed_frontier_idempotency()`：

1. 锁定当前 tenant 下的 Frontier；
2. 若 Frontier 已为 `completed`，读取最新对应 completion Checkpoint；
3. 校验 `checkpoint_state` 与历史 Durable fact 完全一致；
4. 校验 Worker owner 与原 completion fact 一致；
5. 如果存在 `next_identity`，必须按 deterministic identity 找到既有 Next Frontier；
6. 任一 fact 缺失、跨 Execution / Version 或 payload drift，立即拒绝；
7. 全部一致时直接返回既有 `(Checkpoint, Next Frontier)`，不再执行第二次状态推进。

该入口仍然不 `commit`，因此事务职责没有从 progression primitive 外泄。

## 4. 重要边界

### Payload drift

```text
已完成 state = {"result": "A"}
重复请求 state = {"result": "B"}
                    ↓
                 拒绝
```

不能把不同业务结果当作同一个幂等请求。

### Next Frontier 缺失

```text
Current Frontier = completed
Checkpoint = exists
Next Frontier = missing
                    ↓
                 拒绝
```

不能因为 completion 已存在就偷偷创建第二套 completion；这说明原子事务完整性已经被破坏，应暴露异常。

### Cross Execution / Version

既有 Next Frontier 必须仍属于当前 Execution / Workflow Version，防止错误 identity 或历史数据污染导致跨 lineage 收敛。

## 5. 单元测试

新增：

```text
backend/tests/unit/test_frontier_duplicate_completion.py
```

覆盖：

- 已完成终态 Frontier 的相同 completion 直接返回既有 Checkpoint；
- 重复请求 payload drift 时拒绝；
- 非终态重复 completion 必须找到既有 deterministic Next Frontier；
- 重复 completion 不得再次调用 Frontier ownership transition。

本轮未执行 pytest。完整测试将在全部主线任务完成后统一进行。

## 6. 后续边界

本修复解决的是 Durable completion operation 的重复提交收敛，不替代：

- Worker fencing；
- Execution terminalization ownership recheck；
- Next Frontier 数据库唯一约束；
- Recovery expired lease guard；
- Replay Decision Guard。

这些机制继续各自负责对应的一致性边界，并通过统一 `complete_frontier_with_checkpoint()` 组合成完整 Durable progression contract。
