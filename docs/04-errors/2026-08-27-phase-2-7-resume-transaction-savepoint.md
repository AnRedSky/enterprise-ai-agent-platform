# 2026-08-27 Phase 2.7 Resume Transaction Savepoint Boundary

## 问题

`WorkflowExecutionService.resume_from_latest_checkpoint()` 在 Resume 幂等键并发竞争触发 `IntegrityError` 时原先直接调用 `Session.rollback()`。

这会回滚整个调用方事务，而不是只回滚本次 Resume INSERT。对于已经完成 Source Execution row lock、Recovery Assessment 或其他 Durable 写入的 Recovery 流程，这会破坏事务 ownership 与后续状态一致性。

## 根因

```text
Recovery transaction
  ├── Source Execution lock
  ├── latest checkpoint / assessment
  ├── Resume INSERT
  │     └── IntegrityError
  │           ↓
  │       Session.rollback()   ← 错误：回滚整个事务
  └── 后续 Recovery work
```

## 修复

Resume INSERT 改为运行在 SQLAlchemy `begin_nested()` SAVEPOINT 内：

```text
Recovery transaction
  ├── Source Execution lock
  ├── Recovery Assessment
  ├── SAVEPOINT
  │     └── Resume INSERT / flush
  │           └── IntegrityError
  │                 ↓
  │             SAVEPOINT rollback
  ├── 查询既有 Resume
  └── 继续使用原事务
```

竞争失败时只允许当前 Resume INSERT 回滚；随后在原事务内重新读取同 tenant + idempotency key 的 Resume，并继续验证 `resume_of_execution_id` 与 `resume_checkpoint_sequence` lineage。

## 不变量

1. Recovery Service 不得因为 Resume 幂等竞争调用 `Session.rollback()`。
2. Source Execution row lock 必须保持在同一 Recovery transaction 生命周期内。
3. Resume 唯一键竞争只能回滚 SAVEPOINT。
4. 命中已有 Resume 后仍必须重新校验完整 lineage。
5. Resume 创建成功后，Audit / Trace 与 Resume 必须继续由同一外层事务提交。
6. Checkpoint / Recovery durable facts 仍是恢复事实源，Trace 不得替代 durable state。

## Unit Test Contract

新增单元测试验证：

- Resume INSERT 竞争进入 `begin_nested()`；
- `IntegrityError` 后不会调用 `Session.rollback()`；
- SAVEPOINT enter/exit 成功；
- 已存在 Resume 按相同 deterministic idempotency key 返回 `idempotency_hit` 语义；
- lineage 不一致仍拒绝。

## 测试策略

按当前开发策略，仅保留 Unit Test 验证作为主线开发门槛；Backend Full Regression、Real API Acceptance、E2E 与 Release Gate 暂停，不把未实际执行的测试记录为通过。