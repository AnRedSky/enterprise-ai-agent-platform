# 2026-09-03 Operator Governance 单元测试未等待协程警告

## 1. 问题

用户在 Windows 本地执行：

```powershell
cd backend
uv run pytest -q -W error tests/unit/services/runtime_operations/test_operator_governance_transaction.py
```

结果为：

```text
.F.
1 failed, 2 passed
PytestUnraisableExceptionWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited
```

失败测试为 `test_cancel_is_deferred_until_operator_audit_transaction`。

## 2. 根因

该测试直接使用 `AsyncMock()` 作为完整数据库 Session 替身。对于未显式声明的 Session 方法，嵌套 `AsyncMock` 会动态生成异步 mock。测试只关心 `execute`、`commit` 与 `refresh` 三个事务边界，却让整个 Session 暴露大量隐式异步属性，导致测试结束时存在未等待的 mock 协程。

该问题属于测试替身边界错误，不是 Operator Governance 生产事务逻辑错误。

## 3. 修复

新增 `_db_mock()`，只提供当前测试真正需要的异步数据库操作：

- `execute=AsyncMock()`
- `commit=AsyncMock()`
- `refresh=AsyncMock()`

同时增加 `refresh(result)` 的显式等待断言，确保成功路径的事务提交后刷新行为也被验证。

## 4. 验证

本修复已提交到 `main`：

```text
29cada4f3359851d113c5663b141387dbcdef879
fix(test): remove operator governance unawaited coroutine warning
```

当前环境未替用户 Windows 工作树重新执行测试，因此不记录未经实际执行的通过结果。用户应重新执行：

```powershell
cd backend
uv run pytest -q -W error tests/unit/services/runtime_operations/test_operator_governance_transaction.py
```

## 5. 设计约束

后续 AsyncSession 单元测试应优先使用最小显式 Session mock，避免使用无边界的 `AsyncMock()` 模拟整个 Session。测试替身只应暴露被测路径真正调用的异步操作，以便 `-W error` 能够及时发现未等待协程。
