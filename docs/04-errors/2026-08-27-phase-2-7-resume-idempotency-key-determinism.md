# 2026-08-27 Phase 2.7 Resume 幂等键确定性边界

## 问题

Resume Contract 接收 Recovery Assessment 返回的 `resume_idempotency_key`，但此前没有在 Contract 边界再次验证该值是否确实由当前 Source Execution 与 Checkpoint Sequence 按既定规则生成。

## 风险

如果未来新增 Recovery Provider、兼容逻辑或错误的 Assessment 实现返回非确定性幂等键，Resume Domain 可能把同一 Durable Checkpoint 创建成不同的 Resume Identity，破坏 Recovery 重试的确定性。

## 修复

`WorkflowExecutionResumeContractService.resume_with_outcome()` 现在要求：

```text
resume_idempotency_key
    ==
resume:{source_execution_id}:checkpoint:{checkpoint_sequence}
```

不一致立即拒绝，不进入已有 Resume 查询或创建流程。

已有 Resume 命中后仍继续校验 tenant、workflow、workflow version、source execution 与 checkpoint sequence lineage。

## 设计边界

- Recovery Assessment 仍是恢复候选的唯一计算入口。
- Resume Contract 负责校验确定性 Identity，但不复制 Resume 持久化实现。
- 数据库唯一约束仍是最终并发安全兜底。
- Trace 与 Audit 不作为 Resume State Source of Truth。

## 验证

新增 Unit Test 覆盖非确定性幂等键直接拒绝，以及正常 created / idempotency_hit 路径。

当前开发阶段按项目要求暂停完整 Regression / Real API / E2E，仅保留 Unit Test 范围；本环境未实际执行 pytest，因此不得记录为通过。
