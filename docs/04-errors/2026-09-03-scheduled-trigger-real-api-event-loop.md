# Scheduled Trigger Real API 测试事件循环与超时问题

## 1. 现象

直接执行以下命令时，`tests/api_real/test_scheduled_trigger_api.py` 可能表现为长时间无新增输出，尤其在 Scheduler 未产生 Execution 时：

```powershell
uv run pytest -q -W error `
  tests/unit/services/workflow_scheduler `
  tests/api_real/test_scheduled_trigger_api.py `
  -m "unit or real_api" `
  --tb=long
```

历史执行中，三个 Scheduled Trigger Real API 测试分别等待 Execution，单个等待窗口为 20 秒，并叠加 HTTP/数据库异步资源管理成本，最终出现约 85 秒后才集中得到 `FFF` 的体验。

## 2. 根因

原 Real API 测试模块创建 module-scoped `asyncio` event loop，并通过 `_run_async(loop, coroutine)` 在多个同步测试、数据库操作和 Scheduler Runtime 调用之间重复复用该 loop。

同时，`ScheduledTriggerScheduler` 使用独立异步 SQLAlchemy Engine/Session Factory，而测试在相同 module loop 中反复创建、销毁数据库资源。该组合没有形成明确的异步资源生命周期边界，增加了跨测试循环复用连接、fixture teardown 与 Scheduler Runtime 交错的风险。

第二个问题是 Execution 等待逻辑采用固定 20 秒轮询。Scheduler 候选发现条件不满足时，测试不会快速暴露候选数为零这一事实，而会持续等待真实 Execution，导致失败反馈延迟。

## 3. 修复原则

1. Real API 测试不再持有 module-scoped event loop。
2. 每次异步数据库/Scheduler 操作使用一次性 `asyncio.run()`，调用完成后立即销毁 loop。
3. Scheduler Runtime 测试继续使用 `NullPool`，避免跨 loop 复用连接池连接。
4. Real API HTTP client timeout 从 20 秒收紧到 5 秒，服务不可用时快速失败。
5. Execution 轮询从 20 秒收紧到 8 秒，轮询间隔从 1 秒调整为 0.5 秒；超时返回现场数据，由断言输出真实数据库事实。
6. 不在测试中启动、停止、重启 API、Worker、Scheduler、PostgreSQL 或 Redis；服务生命周期仍由 Gate 与开发者手工管理。
7. Gate 继续负责服务健康检查和 tenant-safe context 准备，测试本身负责业务断言。

## 4. 预防规则

涉及异步数据库 Runtime 的同步 Real API 测试，不应跨多个测试复用自建 event loop。若必须运行多个 Scheduler 实例，应在同一次 `asyncio.run()` 中并发执行其 `tick_once()`，完成后立即释放对应 Engine。

任何等待真实 Execution 的测试必须设置有界 timeout，并在 timeout 后直接读取数据库现场，而不是无限等待自然时间流逝。

## 5. 验证

代码修复提交后必须由本地环境实际执行：

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend

uv run pytest -q -W error `
  tests/unit/services/workflow_scheduler `
  tests/api_real/test_scheduled_trigger_api.py `
  -m "unit or real_api" `
  --tb=long
```

如果 Real API 依赖服务未运行，不得自动启动服务；应先按 Gate 输出的标准命令手工启动依赖，再重新执行测试。
