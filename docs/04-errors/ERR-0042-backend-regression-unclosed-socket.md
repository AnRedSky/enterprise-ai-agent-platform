# ERR-0042：Backend 回归中 AsyncEngine 连接池标记遗漏导致 unclosed socket 警告

## 现象

Backend Regression Gate 使用 warnings-as-errors 执行时，`tests/integration/test_tenant_contract_migration.py::test_tenant_contract_migration_casts_bound_uuid_values_for_postgresql` 失败，表面断言本身通过，但 pytest 将未关闭 PostgreSQL socket 提升为 `PytestUnraisableExceptionWarning`：

```text
ResourceWarning: unclosed <socket.socket ... raddr=('::1', 5432)>
PytestUnraisableExceptionWarning: Exception ignored in: <socket.socket ...>
```

因此该问题属于测试资源生命周期错误，而不是 tenant migration 的 UUID CAST 断言错误。

## 根因

`backend/tests/conftest.py` 原先只在测试带有 `integration` 或 `real_api` marker 时调用应用共享 `AsyncEngine.dispose()`。该条件依赖测试作者正确标记所有实际访问数据库的异步测试。

但数据库连接生命周期与 pytest marker 不是同一事实源：任一未标记异步测试只要通过应用共享 Engine 创建连接，连接池就可能跨测试保留。后续测试的同步 teardown / Python socket finalizer 才暴露 `unclosed socket`，导致 warnings-as-errors 门禁失败。

因此不能通过：

- 删除 `-W error`；
- 忽略 `ResourceWarning`；
- 给单个失败测试增加 warning filter；
- 修改 tenant migration 业务代码；

来规避该问题。

## 修复

将测试数据库 Engine 的生命周期边界从“按 marker 条件释放”收敛为“每个异步测试结束统一释放”。`engine.dispose()` 只作用于测试进程中的共享 SQLAlchemy Engine，不启动、重启或停止 PostgreSQL，也不改变生产进程的连接池策略。

这样即使未来新增数据库测试遗漏 marker，也不会把连接带入下一个 pytest 事件循环。

## 预防规则

1. Backend pytest 继续保持 warnings-as-errors。
2. 测试资源释放不得依赖业务 marker 作为唯一条件。
3. AsyncEngine 与 pytest function event loop 必须保持同一生命周期边界。
4. Real API / Integration 测试仍可使用专用 `NullPool` Engine；专用 Engine 必须在测试结束显式 `dispose()`。
5. 不允许通过 warning ignore 隐藏数据库连接泄漏。

## 验证边界

代码修复提交后必须由开发者本地执行：

```powershell
cd backend
uv run pytest -q -W error tests/integration/test_tenant_contract_migration.py
```

随后执行完整 Backend Regression Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

本记录只记录根因与修复，不预填未实际执行的“通过”结果。
