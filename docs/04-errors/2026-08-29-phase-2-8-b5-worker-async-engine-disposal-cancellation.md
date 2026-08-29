# Phase 2.8 B5 Worker AsyncEngine 关闭取消异常

## 1. 现象

开发者在 `main` 最新基线执行 Phase 2.8 B5 Gate 时，Worker shutdown 单元测试在 pytest teardown 阶段失败：

```text
AttributeError: 'AsyncEngine' object attribute 'dispose' is read-only
```

同时直接运行 `uv run python run_worker.py`，Worker 退出过程中出现 asyncpg 连接关闭异常：

```text
asyncio.exceptions.CancelledError
```

## 2. 根因

### 2.1 测试替换方式错误

`sqlalchemy.ext.asyncio.AsyncEngine` 的实例属性 `dispose` 为只读描述符，测试使用 `monkeypatch.setattr(worker_entrypoint.engine, "dispose", ...)` 会在测试 setup/teardown 阶段直接失败。

测试真正需要验证的是 Worker 进程级数据库释放编排，而不是修改第三方 `AsyncEngine` 实例的方法。

### 2.2 Worker 关闭路径未处理 Task cancellation 状态

Worker 在 `finally` 中调用数据库连接池释放时，如果当前主 Task 已经处于 cancellation 状态，`asyncio` 的取消会继续传播到 `engine.dispose()`，进一步进入 asyncpg connection close。若不暂时清除 pending cancellation，连接关闭协程可能在事件循环仍可用时被再次取消，最终产生连接池关闭阶段的 `CancelledError` 异常日志。

## 3. 修复

1. Worker 增加 `_dispose_database_engine()` 正式关闭边界。
2. 正常退出直接等待 `engine.dispose()`。
3. 捕获 `CancelledError` 后暂时通过当前 Task 的 `uncancel()` 清除 pending cancellation。
4. 在仍然有效的事件循环内再次等待 `engine.dispose()` 完成。
5. 清理完成后重新抛出 `CancelledError`，保持原始取消语义，不吞掉进程停止信号。
6. 单元测试改为替换 Worker 入口使用的 `_dispose_database_engine` 函数，而不是修改 `AsyncEngine.dispose` 实例属性。
7. 新增取消期间二次 dispose 的单元测试，验证清理完成后仍恢复 `CancelledError`。

## 4. 验证要求

必须在开发者本地执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_worker_entrypoint.py
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\05_delegation_audit_trace_gate.ps1
```

并实际运行 Worker，确认正常停止后不再出现 asyncpg `CancelledError` 连接关闭异常。

在本记录创建时，以上命令尚未由本次修复执行，因此不得预填 Passed。
