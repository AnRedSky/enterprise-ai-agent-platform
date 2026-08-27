# 2026-08-27 Durable Frontier Progression 一致性 Contract

## 1. 本轮问题

Durable Frontier 已具备 Frontier → Checkpoint → Next Frontier 的原子持久化 primitive，但仅依赖调用方约束仍存在两类高风险输入：

- 没有 Next Frontier 时 Execution 仍被声明为 `running`；
- Next Frontier identity 与当前 Frontier 完全相同，数据库唯一键会把已完成 work item 收敛回自身，造成错误的重新调度语义。

## 2. 修复

新增 `validate_frontier_progression_contract()`，在任何数据库状态变化前校验：

```text
Next Frontier = none
    → Execution = completed

Next Frontier != none
    → Execution = running
    → same Execution
    → same Workflow Version
    → non-empty node_ids
    → identity != current Frontier
```

违反 contract 时直接抛出 `FrontierProgressionContractError`，不会进入 Frontier transition、Checkpoint append 或 Next Frontier enqueue。

## 3. 事务边界

`complete_frontier_with_checkpoint()` 继续保持 caller-owned transaction：

```text
validate contract
      ↓
Frontier fencing transition
      ↓
Checkpoint sequence append
      ↓
Next Frontier idempotent enqueue
      ↓
outer transaction COMMIT
```

本模块不执行 `commit()`。

## 4. 测试

新增 Unit Test 覆盖：

- 当前 Frontier / Next Frontier self-loop identity 拒绝；
- 无 Next Frontier 时必须使用 `completed` Execution status；
- 有 Next Frontier 时必须使用 `running` Execution status；
- 原有原子推进、跨 Execution 拒绝和 terminal checkpoint 行为继续覆盖。

当前环境未实际执行 pytest，因此不记录 Unit Test PASS；完整 Backend / Frontend / E2E / Real API 测试继续按项目当前主线策略暂停。
