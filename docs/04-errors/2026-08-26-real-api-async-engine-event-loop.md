# 2026-08-26 Real API 异步数据库连接跨事件循环错误

## 现象

`tests/api_real/test_workflow_resume_dag_api.py` 连续执行多个 `pytest.mark.asyncio` Real API 用例时，第二个用例在查询 PostgreSQL 时出现：

```text
AttributeError: 'NoneType' object has no attribute 'send'
RuntimeError: Event loop is closed
RuntimeWarning: coroutine 'Connection._cancel' was never awaited
```

错误发生在 SQLAlchemy `AsyncAdaptedQueuePool` 复用 asyncpg 连接时。该连接属于前一个 pytest 异步事件循环，而后续用例运行在新的事件循环中。

## 原因

应用的 `AsyncEngine` 使用默认连接池。生产服务通常长期运行在同一个事件循环，因此该连接池生命周期与生产进程一致；pytest-asyncio 的异步用例可以分别创建事件循环，Real API 测试结束后如果不释放连接池，下一用例可能重新取出绑定已关闭事件循环的 asyncpg Connection。

这属于测试生命周期与异步数据库连接池生命周期不一致，不是 Workflow Resume DAG 业务状态机本身的错误。

## 修复

在 `backend/tests/conftest.py` 增加 Real API 自动 fixture：每个 `real_api` 异步用例结束后调用唯一数据库 `AsyncEngine.dispose()`，释放当前测试事件循环上的连接，避免跨事件循环复用 asyncpg 连接。

生产 `app/infrastructure/db/session.py` 不改变连接池策略，避免为了测试生命周期问题修改生产数据库连接行为。

## 验证要求

必须在本地最新 `main` 上重新执行：

```powershell
uv run pytest -q tests/api_real/test_workflow_resume_dag_api.py -m real_api
```

并继续执行完整 Durable Resume Real API Gate：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\05_run_durable_resume_real_tests.ps1
```

验证标准：DAG 两个 Real API 用例连续执行时不再出现 `Event loop is closed`、`proactor.send` 或 `Connection._cancel was never awaited`；所有业务断言仍必须真实通过。

## 环境注意

Real API Gate 不管理 API、Scheduler、Worker 生命周期。执行前必须停止旧版本 Worker，并由开发者人工启动当前 `main` 对应的 Worker，避免旧 pending Execution、旧代码进程或旧运行配置干扰验收。
