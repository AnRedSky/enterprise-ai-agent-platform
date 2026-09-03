# Operator Governance 最终化失败事务回滚

## 1. 问题

Operator Action 已将 Workflow Execution / Trigger 状态、Result Resource 或 OperatorActionIdempotency 写入当前数据库事务后，治理阶段还需要完成最终幂等事实、AuditLog 与 commit。若其中任一步骤异常，原实现会直接向上抛出异常，但没有统一回滚当前事务。

## 2. 根因

Operator Governance 已正确把领域 Service 的 `commit` 延迟到治理层，但“延迟提交”本身并不等于“失败自动回滚”。最终 `_finish_idempotency()`、`_audit()` 或 `db.commit()` 失败时，SQLAlchemy Session 仍可能持有未提交的 Execution / Trigger / Idempotency / Audit 状态。

该连接若继续被复用，后续请求可能把本应属于失败 Operator Action 的脏状态一起提交，形成跨请求的 partial commit 风险。

## 3. 修复

- `execute_execution()` 的最终 Result Resource / Operator Action / Audit / commit 阶段统一进入事务保护区；任一步失败立即 `rollback()`。
- `execute_trigger()` 同样统一保护 Trigger 状态、Invoke Execution、Operator Action、Audit 与 commit 的最终化阶段。
- 已存在的“业务动作失败后持久化 failed Idempotency”语义保持不变；仅当该失败事实本身的持久化或提交失败时回滚并重新抛出异常。
- 不新增数据库结构，不改变 Worker / Scheduler 并发语义。

## 4. 测试覆盖

新增单元测试覆盖：

1. Run 的 Audit 失败必须 rollback；
2. Cancel 的 Audit 失败必须 rollback；
3. Run 的最终 commit 失败必须 rollback；
4. Trigger Enable 的 Audit 失败必须 rollback；
5. 正常 Run / Cancel 仍只执行一次治理层 commit；
6. 数据库 Mock 显式提供异步 `rollback()`，避免 `-W error` 下产生未等待协程警告。

## 5. 本地验证

代码提交后必须由开发者在本地执行：

```powershell
cd backend
uv run pytest -q -W error tests/unit/services/runtime_operations/test_operator_governance_transaction.py
```

随后按项目治理入口执行 Tenant Safe Real API Gate；Gate 不得自动启动或停止 API、Worker、Scheduler、PostgreSQL、Redis。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

最后执行 Backend Regression：

```powershell
uv run pytest -q -W error
```
