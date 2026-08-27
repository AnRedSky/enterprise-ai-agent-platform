# Durable Frontier Checkpoint — Legacy append Boundary Closure

- 日期：2026-08-27
- 阶段：Phase 2.7 Terminalization / Replay Closure
- 状态：已修复，测试暂缓

## 1. 问题

`WorkflowExecutionCheckpointService` 同时存在 `append()` 与 `append_next_in_transaction()` 两个 Durable Checkpoint 写入口。

此前 `append()` 直接 `db.add()` / `commit()`，没有锁定 `WorkflowExecution`，也没有验证当前 Execution lifecycle、Worker fencing generation 或 sequence 是否为该 Execution 的下一个 Durable sequence。

这构成 Checkpoint Durable Write Boundary 的旁路风险：数据库虽然已有 `(execution_id, sequence)` UNIQUE 约束，但 UNIQUE 只能阻止相同 sequence 的重复写入，不能定义 sequence 的合法分配者，也不能阻止 stale Worker 或 lifecycle drift。

## 2. 修复

`append()` 保留为兼容旧调用方的普通 Checkpoint 入口，但现在必须：

1. 拒绝 `frontier_completed`；该事实必须通过 `append_next_in_transaction()` 并绑定 source Frontier；
2. `WorkflowExecution SELECT ... FOR UPDATE`；
3. 校验 Execution lifecycle；
4. 可选校验 Worker owner / attempt / lease fencing；
5. 查询当前最大 sequence；
6. 要求调用方提供的 sequence 必须正好等于下一个 Durable sequence；
7. 通过上述边界后才允许 INSERT / COMMIT。

因此 legacy `append()` 不再绕过 Execution lock 与 sequence boundary。

## 3. Durable invariant

```text
same Execution
    ↓
Execution row lock
    ↓
current MAX(sequence)
    ↓
requested sequence == next sequence
    ↓
Checkpoint INSERT
```

`frontier_completed` 另外要求：

```text
source Frontier identity
    ↓
append_next_in_transaction()
```

## 4. Unit Test

新增：

```text
backend/tests/unit/test_checkpoint_legacy_append_boundary.py
```

覆盖：

- legacy `append()` 拒绝无 source Frontier 的 `frontier_completed`；
- legacy `append()` 发现 sequence drift 时 fail-closed，不 commit；
- legacy `append()` 在 Execution lock 后接受正确的 next sequence。

## 5. 测试状态

本轮按开发任务要求暂停测试执行。未运行 pytest、Backend Regression、Migration、API、E2E 或本地手动测试，因此不得将任何测试项记录为 PASS。

## 6. 后续审计

继续全仓检查所有 `WorkflowExecutionCheckpoint` 创建路径，确认没有生产代码绕过统一 Durable Write Boundary；随后完成 Success / Failure terminalization 与 Replay convergence 最终审计。