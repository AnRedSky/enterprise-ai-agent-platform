# 2026-09-03 Operator Governance 嵌套 AsyncMock 未等待协程错误

## 1. 问题

在 `uv run pytest -q -W error tests/unit/services/runtime_operations/test_operator_governance_transaction.py` 中，六个断言可以全部通过，但进程退出前仍出现：

```text
RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited
```

这违反项目“警告即错误”的测试要求。

## 2. 根因

Operator Governance 单元测试使用了 `AsyncMock` 作为数据库 `execute()`，其默认 `return_value` 同样是异步 Mock。生产代码对 SQLAlchemy `execute()` 的返回结果执行同步的 `scalar_one_or_none()` / `scalar_one()` 方法。

如果测试继续使用 `AsyncMock().return_value` 作为该结果对象，调用同步结果方法时会创建一个额外的 AsyncMock 协程；该协程没有真实 await 语义，最终在垃圾回收或 pytest teardown 阶段以 `PytestUnraisableExceptionWarning` / `RuntimeWarning` 暴露。

## 3. 修复

测试数据库替身现在显式构造同步 `Mock` 作为 `execute()` 的返回结果，并仅把真正异步的数据库边界保留为 `AsyncMock`：

- `execute`：`AsyncMock`
- `execute` 的结果对象：`Mock`
- `scalar_one_or_none`：同步 `Mock`
- `commit`：`AsyncMock`
- `rollback`：`AsyncMock`
- `refresh`：`AsyncMock`

这样测试模型与 SQLAlchemy AsyncSession 的真实调用语义一致，不再通过隐式嵌套 AsyncMock 制造未等待协程。

## 4. 验证

本次修复需要在开发者本地执行：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
uv run pytest -q -W error tests/unit/services/runtime_operations/test_operator_governance_transaction.py
```

同时必须执行 Backend 默认回归以确认没有其他 AsyncMock 警告：

```powershell
uv run pytest -q -W error
```

## 5. 后续排查原则

如果完整回归仍出现 `AsyncMockMixin._execute_mock_call was never awaited`，必须以完整回归输出和 `PYTHONTRACEMALLOC=1` 的定位信息继续追踪产生协程的具体测试；不得通过关闭 warning、降低 `-W error` 或忽略 teardown warning 掩盖问题。
