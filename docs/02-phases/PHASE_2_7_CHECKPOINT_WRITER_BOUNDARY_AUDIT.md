# Phase 2.7 — Checkpoint Writer Boundary Audit

> 状态：已完成本轮审计，Phase 2.7 整体仍为开发中。
> 基线：`main`，2026-08-27。

## 1. 审计结论

`WorkflowExecutionCheckpoint` 模型已经存在 `(execution_id, sequence)` 数据库唯一约束，因此本轮没有重复增加 migration。

此前 `WorkflowExecutionCheckpointService.append()` 是独立 commit 写入口，没有经过 Execution row lock、Execution lifecycle validation 或 Worker fencing，也没有确认调用方 sequence 是否为当前 Execution 的下一个 Durable sequence。

该入口构成 Durable Checkpoint Write Boundary bypass。

## 2. 已实施修复

`append()` 现在：

- 拒绝 `frontier_completed`；
- 锁定目标 `WorkflowExecution`；
- 校验 tenant（如果调用方提供）；
- 校验 Execution lifecycle；
- 校验可选 Worker owner / attempt / lease fencing；
- 读取当前最大 Checkpoint sequence；
- 要求传入 sequence 等于下一个 Durable sequence；
- 通过边界后才 commit。

Frontier completion 继续只能通过：

```text
append_next_in_transaction()
        ↓
source Frontier binding
        ↓
Execution lock
        ↓
completion idempotency
        ↓
sequence allocation
```

## 3. 当前 Durable Write 模型

```text
                         Checkpoint Writer
                               │
                 ┌─────────────┴─────────────┐
                 ↓                           ↓
        legacy ordinary append       frontier completion
                 │                           │
          Execution FOR UPDATE       append_next_in_transaction
                 │                           │
          lifecycle / fencing         Frontier binding
                 │                           │
          next sequence check         idempotency / fencing
                 └─────────────┬─────────────┘
                               ↓
                         Durable INSERT
```

## 4. Unit Test

新增：

```text
backend/tests/unit/test_checkpoint_legacy_append_boundary.py
```

覆盖 legacy append 的：

- `frontier_completed` boundary rejection；
- sequence drift fail-closed；
- locked Execution + correct next sequence 的正常写入。

测试仅完成实现，尚未执行。

## 5. 下一审计项

继续全仓搜索：

```text
WorkflowExecutionCheckpoint(
db.add(checkpoint)
append(
append_next_in_transaction(
```

确认所有生产写入路径均满足 Durable Write Boundary；重点确认没有隐藏的 `frontier_completed` 直接构造路径。

之后完成：

```text
Success terminalization final audit
        ↓
Failure terminalization final audit
        ↓
Replay convergence final audit
        ↓
Phase 2.7 主线完成判定
```

## 6. 测试策略

当前仍按任务要求暂停完整测试流程。主线开发完成后再统一执行本地自动化测试、迁移验证、API、E2E 与手动验收。