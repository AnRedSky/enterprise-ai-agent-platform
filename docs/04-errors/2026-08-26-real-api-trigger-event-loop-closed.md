# Real API Trigger 测试专用事件循环被 pytest 生命周期提前关闭

## 发生时间

2026-08-26

## 现象

开发者在最新 `main` `23672a6` 执行 Tenant Safe Real API Gate 时，Backend Regression 与 Durable Resume Real API Gate 均通过，但 Scheduled Trigger / Webhook Trigger 真实 HTTP 测试出现：

```text
RuntimeError: Event loop is closed
RuntimeWarning: coroutine ... was never awaited
RuntimeWarning: coroutine 'AsyncEngine.dispose' was never awaited
```

失败集中在 `tests/api_real/test_scheduled_trigger_api.py` 与 `tests/api_real/test_webhook_trigger_api.py`。失败前 HTTP Contract 本身已经完成部分验证，真正进入 PostgreSQL 查询或 Scheduler Runtime 辅助调用时，模块 fixture 保存的 `ProactorEventLoop` 已经被关闭。

## 根因

两个 Real API 测试文件自行创建模块级事件循环，同时调用：

```python
asyncio.set_event_loop(loop)
```

并在 fixture teardown 中主动关闭该循环。

项目同时使用 pytest-asyncio 的测试事件循环生命周期。将自建循环注册为当前事件循环后，pytest 生命周期管理可能在模块测试完成前关闭该循环；随后测试继续通过 `_run_async(loop, coroutine)` 驱动 PostgreSQL 查询，导致 `RuntimeError: Event loop is closed`。

原 fixture 还通过共享的应用 `AsyncEngine` 执行 teardown dispose。该共享 Engine 并不是这些测试的查询入口，反而会扩大跨测试事件循环生命周期耦合，并在循环已经关闭时产生 `AsyncEngine.dispose was never awaited` 的连带 warning。

## 修复

### Scheduled Trigger

`backend/tests/api_real/test_scheduled_trigger_api.py`：

1. 删除共享应用 `AsyncEngine` 导入；
2. 专用测试循环不再调用 `asyncio.set_event_loop(loop)`；
3. PostgreSQL 辅助函数继续各自创建并 `dispose()` 独立 AsyncEngine；
4. fixture teardown 只负责关闭自己创建的事件循环；
5. teardown 增加 `loop.is_closed()` 防护。

### Webhook Trigger

`backend/tests/api_real/test_webhook_trigger_api.py` 使用完全相同的生命周期规则，避免两个 Real API 测试模块形成不同的事件循环管理语义。

## 设计边界

该修复只处理测试基础设施生命周期，不改变 Scheduler、Worker、Trigger、WorkflowRuntime 或 PostgreSQL 业务实现。

测试中的真实 HTTP、真实 PostgreSQL、Scheduler 实例竞争和 Worker 后台生命周期仍必须由实际服务完成验证；不得通过 Mock 或进程内假数据替代 Real API 验收。

## 开发者本地验证

修复代码提交后必须由开发者在本地重新执行：

```powershell
cd backend
uv run pytest -q tests/api_real/test_scheduled_trigger_api.py tests/api_real/test_webhook_trigger_api.py
```

随后执行完整 Backend Gate：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

如果需要直接验证 Tenant Safe Real API：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

本记录只记录已观察到的失败与代码修复事实；在开发者重新执行上述命令之前，不将本修复标记为 Real API 已通过。
