# 2026-08-27 Recovery / Replay lifecycle closure：幂等命中完整性边界

## 问题

Resume Contract 原先在发现相同 `tenant + source execution + checkpoint` 的 Resume 幂等键后，只校验 Resume Execution lineage，然后直接返回 `idempotency_hit`。

如果历史事务或异常恢复遗留了一个 Resume Execution，但其 Bootstrap 没有完成首个 Durable Frontier 入队，那么后续 Recovery 会永久把这个不完整 Resume 当成成功幂等命中，导致 Recovery lifecycle 停在“Resume 已创建”而没有真正进入可调度状态。

## 根因

Resume lifecycle 的幂等键只证明“同一个恢复请求曾创建过 Resume”，不能单独证明 Resume 已经完成：

```text
Source Checkpoint
      ↓
Resume idempotency key
      ↓
已有 Resume
      ↓
原先：直接 idempotency_hit
      ↓
可能隐藏缺失 Frontier 的不完整 Resume
```

## 修复

`WorkflowExecutionResumeContractService.resume_with_outcome()` 在 `idempotency_hit` 返回前增加 Durable Frontier 完整性检查：

- 继续校验 tenant、workflow、workflow version、source execution 与 source checkpoint lineage；
- 查询该 Resume Execution 的 Durable Frontier；
- 没有 Frontier 时立即拒绝，而不是继续返回 `idempotency_hit`；
- 有 Frontier 时才认为 Resume lifecycle 已进入 Durable scheduling boundary；
- 新创建 Resume 仍由既有 Bootstrap 在同一事务内完成 Node lineage 与 Frontier enqueue，不新增第二套 Resume 创建逻辑。

这样形成：

```text
Source Checkpoint
      ↓
Deterministic Resume Identity
      ↓
Resume Execution lineage
      ↓
Completed Node lineage + Durable Frontier
      ↓
idempotency_hit / Worker scheduling
```

## 测试

新增 Unit Test 覆盖：

- 已存在 Resume 但没有 Durable Frontier 时拒绝幂等命中；
- 已存在 Resume 且 Durable Frontier 存在时正常返回 `idempotency_hit`；
- 不创建第二个 Resume，不执行额外 commit。

当前环境无法本地执行 pytest，因此本轮不记录 Unit Test PASS。
