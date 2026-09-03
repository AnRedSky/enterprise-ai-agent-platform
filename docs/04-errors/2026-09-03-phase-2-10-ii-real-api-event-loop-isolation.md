# 2026-09-03 Phase 2.10-II Real API Event Loop 隔离问题

## 现象

Scheduler Real API 验收在本地出现：

- `Scheduled Trigger` 到期后未产生 `WorkflowExecution`；
- 两个独立 `ScheduledTriggerScheduler.tick_once()` 返回后没有产生目标 slot Execution；
- misfire recovery `tick_once()` 返回 `eligible=0 / dispatched=0 / recovered=0`；
- pytest teardown 出现 asyncpg `Future attached to a different loop`。

## 根因

Real API 测试为了验证 Scheduler Runtime，直接在独立测试事件循环中驱动 `ScheduledTriggerScheduler`。原 Runtime 内部固定使用应用全局 `SessionLocal`，而 `SessionLocal` 背后的默认 `AsyncEngine` 使用连接池。

SQLAlchemy AsyncEngine 的池连接不能在不同 asyncio event loop 之间安全复用。Real API 测试同时存在 HTTP/API fixture 生命周期与 Scheduler 专用事件循环，因此全局连接池可能把先前事件循环创建的 asyncpg connection 带入新的事件循环，最终出现跨 loop Future 错误，并使 Scheduler Runtime 验证结果失真。

## 修复

`ScheduledTriggerScheduler` 增加可选 `session_factory` 注入点：

- 生产服务默认继续使用应用唯一 `SessionLocal`，不改变生产数据库基础设施；
- Real API Scheduler 测试创建 `NullPool` 专用 Engine 与 `async_sessionmaker`；
- 两个竞争 Scheduler 实例共享该测试 Session Factory，但每次 Session 获取独立数据库连接；
- 测试结束显式 dispose 专用 Engine，避免连接泄漏到测试事件循环生命周期之外。

## 边界

该修改不是为了绕过 Scheduler 竞争，而是让 Scheduler 的真实 PostgreSQL 原子 Claim、slot 幂等与 misfire 逻辑在一个明确、可控的事件循环/连接池边界中运行。

Gate 仍然禁止自动启动、重启或停止 API / Worker / Scheduler / PostgreSQL / Redis。运行中的外部 Scheduler 仍可合法竞争测试创建的 Trigger；测试不得假设固定 Worker ownership。

## 验证要求

修改后必须至少执行：

```powershell
cd backend

uv run pytest -q -W error `
  tests/unit/services/workflow_scheduler `
  tests/api_real/test_scheduled_trigger_api.py `
  -m "unit or real_api" `
  --tb=long

powershell -NoProfile -ExecutionPolicy Bypass `
  -File .\scripts\test\release\01_backend_regression_gate.ps1
```

真实 API 结果必须以开发者本地实际执行输出为准；本文档不预填通过结论。
