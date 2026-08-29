# Worker 进程退出阶段 asyncpg CancelledError

## 1. 现象

2026-08-29 本地运行 `uv run python run_worker.py` 时，Worker 主循环本身可以启动，但进程退出阶段出现：

```text
Exception closing connection <AdaptedConnection ...>
asyncio.exceptions.CancelledError
```

异常来自 SQLAlchemy asyncpg 连接池在事件循环进入取消/关闭阶段后，延迟执行异步连接关闭。

## 2. 根因

Worker 入口原先只在 `run_forever()` 返回后调用 `worker.stop()`，没有显式管理进程级 AsyncEngine 生命周期。Worker Runtime 内部虽然使用 `async with SessionLocal()` 释放业务 Session，但 AsyncEngine 连接池仍由全局对象持有。

当进程因停止信号退出并进入 `asyncio.run()` 的事件循环收尾阶段时，池中尚未及时完成关闭的 asyncpg connection 可能在取消阶段执行 `connection.close()`，从而抛出 `asyncio.CancelledError`。

该问题不属于业务事务失败，也不应通过吞掉 `CancelledError` 或降低日志级别规避；正确边界是让 Worker 在事件循环仍有效时显式 dispose AsyncEngine。

## 3. 修复

`app/entrypoints/worker.py` 新增进程级 `_dispose_database_engine()`：

1. Worker 主循环退出后执行 `worker.stop()`；
2. 在事件循环关闭前执行 `await engine.dispose()`；
3. 如果清理本身收到 `CancelledError`，先重新执行一次 dispose，再把取消继续向上传播；
4. 新增单元测试验证 Worker Service 返回前一定调用 AsyncEngine dispose。

## 4. 边界

- 不修改 Workflow Execution 状态机；
- 不修改 Worker lease / heartbeat；
- 不新增数据库连接池；
- 不吞掉真正的进程取消信号；
- 不要求启动额外服务。

## 5. 验证要求

修复提交后的本地验证必须至少执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_worker_entrypoint.py
uv run pytest -q
uv run python run_worker.py
```

Worker 正常启动后，通过开发者使用的正常停止方式退出，退出日志不得再出现上述 `Exception closing connection` / `asyncio.exceptions.CancelledError`。

未由开发者实际执行前，不标记为 Passed。
