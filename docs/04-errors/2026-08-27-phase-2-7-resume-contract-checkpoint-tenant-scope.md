# Phase 2.7-A：Resume Contract Checkpoint 查询缺少 tenant scope

## 1. 发现

Phase 2.7-A 已要求 Node completed facts 与 Checkpoint Recovery 均保持当前 Execution 的 tenant boundary。继续检查正式 Resume Contract 时发现：`WorkflowExecutionResumeContractService.resume_with_outcome()` 在锁定 Source Execution 后调用 `CheckpointService.latest()` 时没有传入 `locked_execution.tenant_id`。

## 2. 影响

- Automatic Recovery 的入口已经带 tenant scope，但正式 Resume Contract 又退回无 scope 查询；
- Recovery Domain 的安全边界依赖上游，而不是在 Checkpoint lookup 自身闭环；
- 未来跨租户错误 ID 注入时，Resume candidate 评估路径缺少最后一道 tenant predicate。

## 3. 修复

Resume Contract 现在统一执行：

```text
Source Execution
      ↓ lock
locked_execution.tenant_id
      ↓
Checkpoint.latest(execution_id, tenant_id=locked_execution.tenant_id)
      ↓
Resume assessment
```

没有新增第二套 Checkpoint 查询实现，继续复用 `WorkflowExecutionCheckpointService.latest()`。

## 4. 单元测试

新增 `backend/tests/unit/test_workflow_resume_contract_tenant_scope.py`，验证 Resume Contract 的第一条 Checkpoint SQL 同时包含 Execution ID 与 tenant scope。

当前环境未执行 pytest，因此测试状态保持“待开发者本地执行”，不得记录 PASS。
