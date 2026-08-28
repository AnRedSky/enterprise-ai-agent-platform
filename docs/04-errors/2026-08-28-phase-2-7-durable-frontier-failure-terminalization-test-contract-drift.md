# 2026-08-28 Phase 2.7 Durable Frontier failure terminalization 回归测试契约漂移

## 1. 现象

开发者基于 `main` 最新提交 `40765ae` 实际执行 Durable Frontier failure terminalization targeted tests：

```text
9 tests collected
3 failed, 9 passed
```

失败位置：

- `tests/unit/test_frontier_failure_terminalization.py::test_failure_terminalization_closes_active_sibling_frontiers`
- `tests/unit/test_frontier_failure_transaction.py::test_failure_terminalization_is_transaction_local`
- `tests/unit/test_frontier_failure_transaction.py::test_already_failed_execution_does_not_duplicate_failure_fact`

## 2. 根因

本轮失败不是生产实现放宽或错误，而是测试 double 与已经完成的 Durable Frontier Failure Terminalization Contract 不一致：

1. `test_failure_terminalization_closes_active_sibling_frontiers` 通过 `str(Update)` 断言 `failed`。SQLAlchemy 默认编译会把更新值参数化为 `:status`，因此 SQL 文本只证明存在参数，而不会把字符串值 `failed` 展开。
2. 两个 transaction-local 测试使用只包含 `pass` 的 `_DB` double，但当前生产方法设计要求在同一事务中调用 `_mark_active_sibling_frontiers_failed(db, ...)`。测试没有替换该事务内副作用，导致 `AttributeError: '_DB' object has no attribute 'execute'`。
3. `status=failed` 时生产实现仍需要关闭同 Execution 的活动 sibling Frontier，但不得再次写入 Execution failure trace / audit fact。原测试只验证后者，未表达前者。

## 3. 修复

- SQLAlchemy Update 测试改为检查编译参数 `compiled.params`，验证实际绑定值而不是依赖默认 SQL 字符串渲染。
- transaction-local 测试显式使用 `AsyncMock` 替换 sibling Frontier terminalization helper，并断言收到的仍是同一个事务 `db`，从而验证事务边界而不是要求测试 double 实现数据库。
- 已失败 Execution 的重复 failure 测试同时验证 sibling Frontier helper 仍在当前事务执行一次，但 governance trace / audit 不重复生成。
- `backend/scripts/test/workflow/01_resume_runtime_regression.ps1` 纳入上述两个 failure terminalization 测试文件，使本轮回归成为单一、可重复执行入口。

## 4. 防止复发

测试不得通过过度具体的 SQL 字符串格式断言绑定参数值；应优先检查编译参数、表达式结构或实际数据库结果。

涉及事务边界的 Unit Test 必须明确替换跨层数据库副作用，并断言调用发生在传入的同一 session 上；不得让 mock 因缺失 `execute` 等基础设施方法掩盖真正的业务断言。

## 5. 验证要求

修复后必须由开发者在本地实际执行：

```powershell
cd backend
uv run pytest -q `
  tests/unit/test_frontier_duplicate_completion.py `
  tests/unit/test_frontier_duplicate_consumption.py `
  tests/unit/test_frontier_failure_terminalization.py `
  tests/unit/test_frontier_failure_transaction.py `
  tests/unit/test_frontier_claim_lock_order.py

powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\workflow\01_resume_runtime_regression.ps1
```

本记录不预填 PASS；最终结果以开发者实际执行输出为准。
