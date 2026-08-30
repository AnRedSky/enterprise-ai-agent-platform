# Scheduler 生命周期测试残留异步连接警告

## 1. 发现时间

2026-08-30

## 2. 影响范围

- `backend/tests/unit/test_service_entrypoints.py`
- `backend/app/entrypoints/scheduler.py`
- Scheduler Service 生命周期单元测试

## 3. 现象

Backend 全量回归：

```text
940 passed, 3 skipped, 63 deselected, 1 warning
```

警告：

```text
RuntimeWarning: coroutine 'Connection._cancel' was never awaited
```

警告由 pytest 结束阶段的 `_pytest.stash` 清理触发，表明测试期间存在未正确收敛的异步数据库连接/后台任务。

## 4. 根因分析

`run_scheduler_service()` 当前同时监督四个长期运行循环：Scheduled Trigger、Workflow Recovery、Runtime Alert、Runtime Notification。

测试最初只替换 Scheduled Trigger 与 Workflow Recovery 两个调度器，而生产入口已经增加 Runtime Alert / Runtime Notification 两个正式循环。未被替换的两个循环会在单元测试事件循环中执行真实实现，可能创建数据库 Session / 连接；随后测试通过 `asyncio.run` 生命周期结束时进入连接取消路径，最终产生 `Connection._cancel` 未等待警告。

因此问题不是 asyncpg 本身的连接关闭实现，而是测试替身没有覆盖生产入口当前全部后台依赖，导致单元测试混入真实 Runtime Scheduler 副作用。

## 5. 修复方案

将 `test_service_entrypoints.py` 的三个 Scheduler 生命周期测试全部扩展为四路 Mock：

- `ScheduledTriggerScheduler`
- `WorkflowRecoveryScheduler`
- `RuntimeAlertScheduler`
- `RuntimeNotificationScheduler`

同时对四个对象统一断言构造参数、`run_forever()` 调用和 `stop()` 收敛行为。

不修改生产 Scheduler 生命周期，不引入兼容层，也不通过忽略 RuntimeWarning 掩盖资源泄漏。

## 6. 回归要求

```powershell
cd backend
uv run pytest -q tests/unit/test_service_entrypoints.py
uv run pytest -q
```

要求最终无 RuntimeWarning。
