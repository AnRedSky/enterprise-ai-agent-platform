# Worker AsyncEngine 关闭阶段 CancelledError

## 1. 发生时间

2026-08-29

## 2. 现象

本地执行 `uv run python run_worker.py` 时，Worker 启动后出现 SQLAlchemy asyncpg 连接关闭异常：

```text
Exception closing connection <AdaptedConnection <asyncpg.connection.Connection ...>>
asyncio.exceptions.CancelledError
```

异常位于 SQLAlchemy AsyncEngine / asyncpg connection close 路径，而不是 Worker Runtime 业务执行路径。

## 3. 根因分析

Worker 进程退出时需要关闭 AsyncEngine 连接池。此前 `_dispose_database_engine()` 直接 `await engine.dispose()`；如果主 Task 已经收到取消请求，取消语义可能在连接池内部关闭 asyncpg connection 时继续向下传播，导致连接关闭阶段出现 `CancelledError`。

原实现随后通过取消计数消费并再次调用 `engine.dispose()` 恢复清理，但第一次 dispose 已经被取消，无法保证所有底层 connection close coroutine 在同一个事件循环生命周期内稳定完成。

该问题属于进程级资源清理的取消边界问题，与业务 Runtime、Lease 或 PostgreSQL Claim 语义无关。

## 4. 修复

`app/entrypoints/worker.py` 的 `_dispose_database_engine()` 改为：

1. 先创建独立的 `engine.dispose()` Task；
2. 使用 `asyncio.shield()` 防止主 Task cancellation 直接取消连接池清理；
3. 如果主 Task 收到取消，消费当前 cancellation 计数并等待同一个 dispose Task 完成；
4. 清理完成后重新抛出 `asyncio.CancelledError`，不吞掉原停止语义；
5. 非取消型 dispose 异常继续向上抛出，避免隐藏真正的数据库资源清理故障。

同时增加 Worker entrypoint 单元测试，覆盖：

- 正常 Worker 退出后的 engine dispose；
- cancellation 下完成 shielded dispose 并恢复取消语义；
- 非取消型 dispose 异常继续传播。

## 5. 验证结果

后续修复已进入 B6 正式验收闭环。最新 B6 Gate 全部通过：

```text
Delegation Claim + Worker dispatch Unit/Contract
38 passed in 1.08s

Backend default regression
870 passed, 3 skipped, 52 deselected in 34.61s

Migration/head
0039_workflow_node_execution_tenant_trigger (head)

Real HTTP + PostgreSQL multi-worker Durable Frontier Runtime
5 passed in 7.48s

[PASS] Phase 2.8 B6 multi-worker Delegation Runtime gate completed.
```

此外 Worker shutdown cancellation 的 targeted unit coverage 已作为 B6 修复链的一部分通过；当前没有新的证据表明该 AsyncEngine cleanup 问题仍阻塞运行时验收。

## 6. 状态

**已修复并已验证。**

该错误继续保留作为工程追溯记录，但不再作为当前 Phase 2.8 blocker。后续若再次出现 shutdown resource cleanup 回归，应基于新的实际日志建立新的错误记录，而不是覆盖本记录的已关闭状态。
