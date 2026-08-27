# Phase 2.7 Resume Idempotency Lineage Drift

- 日期：2026-08-27
- 阶段：Phase 2.7-A Durable Recovery Closure
- 类型：Recovery / Resume / Idempotency Boundary
- 状态：已修复

## 问题

Resume Contract 在命中确定性 `idempotency_key` 时，原实现只校验：

- `resume_of_execution_id`
- `resume_checkpoint_sequence`

但没有完整验证已存在 Resume 的 tenant、workflow 与 workflow version lineage。

因此，异常历史数据如果复用了同一个租户幂等键，即使 Source / Checkpoint 字段表面匹配，也可能被错误地作为合法 idempotency hit 返回。

## 修复

`WorkflowExecutionResumeContractService.resume_with_outcome()` 在 idempotency hit 路径增加完整 lineage 校验：

```text
Tenant
  + Workflow
  + Workflow Version
  + Source Execution
  + Checkpoint Sequence
       ↓
Resume Idempotency Hit
```

任一字段不一致立即拒绝，不继续创建或恢复执行。

## 并发边界

同一 Source Execution 的正式 Resume 路径继续先锁定 Source row；数据库 `(tenant_id, idempotency_key)` 唯一约束继续作为最终并发安全兜底。

## 测试

新增 Unit Contract 覆盖已有 Resume 的 workflow lineage drift；未执行完整 Backend Regression / Real API Acceptance，遵循当前开发策略。
