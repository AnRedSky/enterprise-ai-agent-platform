# Phase 2.10-II Durable Resume Operator Action 幂等审计缺口

- 发现日期：2026-09-02
- 发现阶段：Operator Action Result Lineage 收敛后代码审阅
- 关联任务：#84
- 影响范围：Backend / Operator Governance / Durable Resume

## 现象

`WorkflowExecutionService.resume_from_latest_checkpoint()` 已根据 `tenant + 原始 Execution + checkpoint sequence` 生成确定性的 Workflow Execution `idempotency_key`，因此同一 Checkpoint 的 Resume 会复用同一个 Result Resource。

但 `OperatorActionGovernanceService.execute_execution()` 原先仅对 Retry 使用客户端 Idempotency-Key。Resume 没有登记 Operator Action 幂等事实，重放请求会再次进入治理层 Audit 写入流程。

结果是：底层 Result Resource 幂等，而 Operator Action / Operator Audit 不是幂等，破坏了 `Operator Action -> Audit -> Result Resource -> Execution/Trace` 治理链的一致性。

## 根因

两层幂等边界没有收敛：

1. Workflow Execution Resume 已有确定性内部幂等键；
2. Operator Action Governance 未把该事实提升为 Operator Action 的租户级幂等键；
3. 因而 Governance 无法在进入领域 Resume 服务前识别同一 Resume 请求的已完成 Operator Action；
4. Resume 服务虽然复用 Result Resource，但 Governance 仍可能重复创建 AuditLog。

## 修复

`OperatorActionGovernanceService.execute_execution()` 现在在 Resume 且客户端未提供 Idempotency-Key 时自动生成：

```text
internal:resume:{execution_id}:{checkpoint_sequence}
```

该内部键仅用于治理层事实收敛，不要求客户端填写，也不改变公开 API 的请求契约。

首次 Resume：

```text
claim Operator Action(started)
  -> Resume Result Resource
  -> Operator Action(succeeded)
  -> Operator Audit
  -> commit
```

同一 Resume 重放：

```text
claim existing Operator Action
  -> reuse Result Resource
  -> return
```

因此不会再次创建 Operator Audit。

## 本次本地反馈的测试根因

首次新增 Real PostgreSQL Acceptance 时，测试夹具错误地把 `checkpoint_reason="node_failed"`、`execution_status="failed"`、`node_status="failed"` 作为 Resume Checkpoint。

这与生产恢复评估契约冲突：Durable Resume 只接受 `node.completed` 或 `frontier_completed` Checkpoint；Checkpoint 产生时的 `execution_status` 必须是 `running`，其中 `node.completed` 还必须绑定 completed Node。原始 Execution 在恢复前仍然可以是 `failed`，两者不是同一状态语义。

因此本次 `409 当前 Workflow Execution 状态不允许执行该 Operator Action` 是 **Acceptance fixture 错误，不是 Operator Governance 生产逻辑错误**。测试已修正为真实可恢复边界：`execution.status=failed` + `checkpoint.execution_status=running` + `checkpoint_reason=node.completed` + `node_status=completed`。

## 验证要求

必须在本地执行：

```powershell
cd backend
uv run pytest -q -W error tests/api_real/test_operator_action_resume_lineage_acceptance.py -m real_api
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.10\25_operator_action_result_lineage_gate.ps1
uv run pytest -q -W error
```

Real PostgreSQL 测试会自动生成并清理 Tenant、User、Workflow、Execution、Checkpoint、Idempotency-Key 与 Audit/Trace 数据；Gate 不创建、启动、重启或停止 API、Scheduler、Worker、PostgreSQL、Redis。

## 状态

代码与 Acceptance 已修正，等待开发者本地实际执行结果；在获得本地输出前不得记录为“通过”。