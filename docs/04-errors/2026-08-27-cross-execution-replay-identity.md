# Cross-Execution Replay Identity 边界错误记录

## 发现

Recovery Candidate 的 `assess()` 接收 `execution_id` 与 `checkpoint` 两个独立对象，但此前只校验 Checkpoint 的 reason、execution status 和 Node Fact 完整性，没有显式验证 `checkpoint.execution_id == execution_id`。

这会让错误调用方有机会把另一个 Workflow Execution 的 Durable Checkpoint 交给当前 Recovery Candidate，形成跨 Execution Replay snapshot。

## 根因

Replay identity 原先主要依赖 `execution_id + checkpoint_sequence` 生成 Resume idempotency key，但 Candidate 评估入口没有把 Checkpoint 所属 Execution 作为前置领域不变量强制验证。

## 修复

在 Recovery Candidate 进入任何可恢复边界判断前增加：

```text
checkpoint.execution_id == execution_id
```

不一致立即抛出 `ValueError`，禁止继续生成 Resume Candidate。

该校验属于 Recovery Domain Service 的只读 invariant，不复制 Planner、Runtime 或 Checkpoint persistence 逻辑。

## 生命周期边界

```text
Source Execution
      ↓
Source Checkpoint
      ↓
Recovery Candidate
      ├─ execution identity match      ✓
      ├─ checkpoint boundary           ✓
      ├─ Node Fact integrity           ✓
      └─ resume idempotency identity   ✓
      ↓
Resume Execution
```

## 测试

新增 Unit Test 覆盖跨 Execution Checkpoint 被拒绝。

当前阶段继续暂停完整 Regression / E2E；本环境没有实际执行 pytest，因此不得将该 Unit Test 标记为 PASS。