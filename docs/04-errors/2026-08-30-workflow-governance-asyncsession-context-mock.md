# Workflow Governance AsyncSession 事务 Mock 契约缺失

## 1. 发现时间

2026-08-30

## 2. 影响范围

- `backend/tests/unit/test_workflow_execution_governance.py`
- `backend/app/services/integration/publisher.py`
- `WorkflowExecutionService.cancel()` 治理审计单元测试

## 3. 现象

执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_workflow_execution_governance.py
```

失败为 `1 failed, 3 passed, 1 warning`。

失败发生在 `RuntimeIntegrationEventPublisher.publish()`：

```text
TypeError: 'coroutine' object does not support the asynchronous context manager protocol
```

同时产生：

```text
RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited
```

## 4. 根因分析

测试使用 `AsyncMock()` 作为数据库 Session。未显式配置时，`db.begin_nested()` 被模拟成 coroutine。

生产实现使用：

```python
async with self.db.begin_nested():
```

`AsyncSession.begin_nested()` 的生产契约是同步调用后返回异步上下文管理器，而不是返回 coroutine。因此通用 `AsyncMock` 无法准确表达该混合异步 Session API。

这属于测试替身接口契约错误，不属于 `RuntimeIntegrationEventPublisher` 事务实现错误。

## 5. 修复方案

仅在该单元测试中覆盖事务边界：

```python
from contextlib import nullcontext

db.begin_nested = Mock(return_value=nullcontext())
```

保持：

- `db.flush()` 为 `AsyncMock`；
- `db.add()` 为同步 `Mock`；
- 生产 Publisher 不修改；
- 不增加运行时兼容分支。

## 6. 回归要求

至少执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_workflow_execution_governance.py
uv run pytest -q
```

必须同时确认该测试通过且不再产生 `RuntimeWarning`。

## 7. 测试边界

该单元测试不得启动 API、Worker、Scheduler、PostgreSQL 或 Redis。真实 Runtime Acceptance 继续由独立 Gate 执行，并仅探测依赖服务状态。
