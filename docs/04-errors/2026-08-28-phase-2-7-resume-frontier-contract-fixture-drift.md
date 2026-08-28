# Phase 2.7 本地回归：Resume / Frontier Contract Fixture Drift

- 日期：2026-08-28
- 阶段：Phase 2.7 本地回归修复
- 来源：开发者本地 `uv run pytest` 实际执行结果
- 影响范围：Durable Resume Contract、Frontier Replay / Terminalization、Worker epoch 与 tenant candidate 单元测试

## 实际失败结果

### Durable Resume targeted

```text
15 passed, 1 failed
```

失败：

- `tests/unit/test_workflow_resume_contract_tenant_scope.py::test_resume_contract_reads_checkpoint_with_locked_execution_tenant_scope`
- 原因：测试中的 `SimpleNamespace` checkpoint 未提供正式 Contract 使用的 `execution_id` 字段；生产 `WorkflowExecutionCheckpointRecoveryService.assess()` 会校验 checkpoint 与 locked Source Execution 的 lineage。

### Frontier targeted

```text
37 passed, 6 failed
```

失败集中在：

- terminal Replay fixture 未提供生产实现现在需要的 locked Execution 查询结果；
- terminalization fixture 将 Execution result 直接作为当前 Frontier idempotency 查询结果，导致后续 lifecycle 查询错位；
- non-terminal completion fixture 未补齐 Next Frontier Node overlap 查询的空结果；
- tenant candidate 测试直接依赖 SQL 字符串包含 bound value，而 SQLAlchemy 默认编译会将字符串作为 bind parameter；
- Worker epoch 测试依赖已不存在的注释文本，而生产实现已经通过 `execution.worker_attempt` 与 checkpoint fencing 参数表达该规则。

## 修复

本轮修复仅调整测试 Contract / double，使测试真实反映当前生产 Durable contract，不通过降低生产约束来让测试通过。

- Resume tenant checkpoint fixture 补齐 `execution_id` lineage 字段；
- Frontier terminal Replay fixture 补齐 locked Execution 查询，并验证 checkpoint lifecycle 与 Execution lifecycle 一致；
- Frontier terminalization fixture 按真实查询顺序提供 current Frontier、Execution 与 active sibling Frontier double；
- tenant candidate 测试改为验证 SQLAlchemy 编译后的 bound lifecycle values，而不是依赖 SQL 字符串内联值；
- Worker epoch 测试改为验证 Frontier `attempt`、Execution `worker_attempt` 与 checkpoint `expected_worker_attempt` 的实际行为契约。

## 验证边界

以上修复提交后尚未由开发者重新执行本地 pytest，因此不得记录为 PASS。下一步必须重新执行 Resume targeted、Frontier targeted，以及完整 `01_resume_runtime_regression.ps1`，以确认是否进入下一组真实失败。
