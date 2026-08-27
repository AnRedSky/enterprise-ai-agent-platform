# 2026-08-27 Phase 2.7 Recovery Trace Checkpoint Lineage

## 问题

Recovery → Resume 建立 Trace lineage 时，原实现只保存 `source_execution_id` / `resume_execution_id` / `trace_id`，没有验证 Resume Execution 的 `resume_checkpoint_sequence` 是否确实属于 Source Execution，也没有阻止跨 tenant / workflow version 的错误关联。

这会使 Trace lineage 在审计上看起来存在，但无法证明它对应了同一个 Durable Recovery checkpoint 边界。

## 修复

`WorkflowRecoveryTraceLinkService.link()` 在创建 `recovery.trace_linked` 前执行：

```text
Source Execution
      ↓
Resume.resume_of_execution_id == Source.id
      ↓
tenant_id 相同
      ↓
workflow_version_id 相同
      ↓
resume_checkpoint_sequence 非空
      ↓
Source Checkpoint(sequence) 存在
      ↓
创建 Recovery Trace lineage
```

事件 metadata 同时保存 `resume_checkpoint_sequence`，用于后续 lineage audit。

## 边界

- Trace 仍然不是 Recovery state source of truth；
- 不读取或复制 Checkpoint `state_data` 到 Trace；
- 不新增 Scheduler / Worker ownership 逻辑；
- 不新增第二套 Recovery Planner；
- 不新增 migration，复用现有 `WorkflowExecution.resume_checkpoint_sequence` 与 Checkpoint sequence。

## 验证

新增 Unit Test：

```text
backend/tests/unit/test_workflow_recovery_trace_lineage.py
```

覆盖错误 Source 关联、不存在 checkpoint、合法 checkpoint lineage 三种情况。

当前仓库环境未实际执行 pytest，因此不能将该 Unit Test 标记为 PASS。
