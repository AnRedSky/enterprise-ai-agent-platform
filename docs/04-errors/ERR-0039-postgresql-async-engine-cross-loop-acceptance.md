# ERR-0039：PostgreSQL Real Acceptance 跨事件循环复用 AsyncEngine 连接

## 1. 现象

Backend Regression 在 `test_operator_action_audit_result_lineage_is_tenant_scoped` teardown 阶段出现：

- `RuntimeError: Event loop is closed`
- `AttributeError: 'NoneType' object has no attribute 'send'`
- `RuntimeWarning: coroutine 'Connection._cancel' was never awaited`

Phase 2.10 Operator Action Result Lineage Gate 本身正常通过，但完整 Backend Regression 因该 integration test 被阻塞。

## 2. 根因

测试使用全局生产 `AsyncEngine`，而 pytest-asyncio 为异步测试提供 function-scoped event loop。SQLAlchemy AsyncEngine 默认连接池会缓存绑定旧 event loop 的 asyncpg Connection。测试切换到新的 event loop 后再次取得连接，导致旧连接仍引用已经关闭的 Windows ProactorEventLoop。

该问题属于测试资源生命周期错误，不属于 PostgreSQL 服务故障，也不应通过启动或重启数据库解决。

## 3. 修复

`test_operator_action_result_correlation_acceptance.py` 改为在测试内部创建独立 `AsyncEngine`，使用 `NullPool`，并在测试结束后显式 `dispose()`。

这样测试连接不会跨 event loop 复用，同时保持生产 `app.infrastructure.db` 的连接池配置不变。

## 4. 验证

必须执行：

```powershell
cd backend
uv run pytest -q -W error tests/api_real/test_operator_action_result_correlation_acceptance.py -m integration
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

## 5. 约束

- 不修改生产 PostgreSQL AsyncEngine 为 `NullPool`。
- 不自动启动、重启或停止 PostgreSQL、Redis、API、Worker、Scheduler。
- warnings-as-errors 保持开启。
- 测试身份与测试数据继续由测试自动生成。
