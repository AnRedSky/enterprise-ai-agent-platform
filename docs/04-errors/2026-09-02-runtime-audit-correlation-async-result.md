# Runtime Audit Correlation 异步查询结果消费错误

## 1. 现象

Backend regression 在 `-W error` 下出现两项失败：

- `test_by_operator_action_without_execution_keeps_requested_page_size`
- `test_by_operator_action_rejects_untyped_result_as_execution`

失败位置均为 `RuntimeAuditTraceCorrelationService._operator_action()`：

```text
AttributeError: 'coroutine' object has no attribute 'scalar_one_or_none'
```

## 2. 根因

`AsyncSession.execute()` 是异步调用，必须先 `await` 得到 SQLAlchemy `Result`，再调用 `scalar_one_or_none()`。

原实现把 `.scalar_one_or_none()` 绑定在 `execute(...)` 调用表达式上，实际效果等价于：

```python
(awaitable).scalar_one_or_none()
```

而不是：

```python
result = await db.execute(statement)
return result.scalar_one_or_none()
```

因此运行时得到 coroutine，而不是 SQLAlchemy Result。

## 3. 修复

`_operator_action()` 与同类 `_audit()` 查询统一改为：

1. 构造 tenant-scoped statement；
2. `await self.db.execute(statement)`；
3. 对已取得的 Result 调用 `scalar_one_or_none()`。

没有修改 tenant boundary、查询条件或业务语义。

## 4. Teardown Warning

`test_trace_focus_is_returned_outside_the_paginated_page` 在 `-W error` 下还暴露了 `PytestUnraisableExceptionWarning`，根源是该测试已经 mock 掉全部 DB-facing collaborator，却仍给 Service 注入 `AsyncMock()` DB 对象，导致未使用的异步 mock coroutine 在 teardown 阶段被发现。

测试改为注入 `MagicMock()` DB；真正需要异步行为的 service collaborator 仍使用 `AsyncMock()`。这样测试表达的是实际隔离边界，也不会制造无意义的未 await coroutine。

## 5. 验证要求

必须在开发者本地执行：

```powershell
cd backend
uv run pytest -q -W error tests/unit/test_runtime_audit_trace_correlation.py tests/unit/test_runtime_correlation_focused_facts.py
uv run pytest -q -W error
```

若出现新的 warning，在 Backend Gate 中按错误处理，不得通过关闭 warning 或降低 `-W error` 规避。
