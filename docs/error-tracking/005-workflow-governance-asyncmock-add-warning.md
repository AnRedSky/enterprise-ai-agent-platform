# 005：Workflow Governance 测试使用 AsyncMock 导致 `db.add()` 未 await 警告

## 1. 基本信息

- 阶段：Phase 1.5-E Governance / Audit / Trace
- 日期：2026-08-20
- 类型：Backend Test / Async Session Mock
- 严重级别：中
- 影响范围：Backend full regression / Phase 1.5-E validation

## 2. 实际反馈

开发者执行 `uv run pytest -q`：

```text
180 passed, 4 warnings
RuntimeWarning: coroutine 'AsyncMockMixin._execute_mock_call' was never awaited
```

警告位置：

```text
app/services/workflow_governance.py:35
app/services/workflow_governance.py:56
```

对应代码为：

```python
self.db.add(event)
```

生产实现符合 SQLAlchemy `AsyncSession` contract：`add()` 是同步方法，而 `flush()` 才是异步方法。

## 3. 根因

状态机测试将整个数据库 Session 设置为 `AsyncMock()`：

```python
db = AsyncMock()
```

这会使未显式覆盖的同步 `db.add()` 也变成 `AsyncMock`。生产代码调用 `self.db.add(event)` 时返回未 await 的 coroutine，从而产生 RuntimeWarning。

这不是生产异步逻辑错误，而是测试 double 与 SQLAlchemy Session API 的同步/异步方法边界不匹配。

## 4. 修复方案

测试保留 `AsyncMock` 用于异步 Session 方法，同时显式覆盖同步方法：

```python
from unittest.mock import AsyncMock, Mock


def _db() -> AsyncMock:
    db = AsyncMock()
    db.add = Mock()
    db.refresh = AsyncMock()
    return db
```

这样：

- `db.add()` → 同步 Mock；
- `db.flush()` → AsyncMock；
- `db.refresh()` → AsyncMock；
- 不修改生产 `WorkflowGovernanceService`。

## 5. 预防措施

- Async SQLAlchemy 测试 double 必须区分同步 Session API 与异步 Session API。
- `AsyncSession.add()` 不得被错误模拟为 coroutine。
- 新增 Session 方法调用时，应检查其真实 SQLAlchemy API 是否为 sync/async。
- Backend full regression 要求 0 warning，不仅要求 tests passed。
- 新发生的工程错误继续独立记录在 `docs/error-tracking/`。

## 6. 验证要求

重新执行：

```powershell
cd backend
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_phase_1_5_e_workflow_governance_validation.ps1
```

预期：

```text
180 passed, 0 warnings
Phase 1.5-E Backend validation completed.
```

## 7. 状态

已在 `main` 修复测试 double，等待开发者本地重新执行验证确认 0 warning。
