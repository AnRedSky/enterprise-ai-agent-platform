# Phase 2.10-II Real API Scheduler / Worker Runtime 问题记录

## 1. 现象

Backend Regression 已达到 `1050 passed, 7 skipped, 80 deselected`，Migration head 校验通过；Tenant-safe Real API 仍有 Scheduler 与 Delegation 多 Worker 场景失败。

本次本地事实包括：

- Scheduled Trigger Real API 未产生 Execution。
- Scheduled Trigger 双 Scheduler 合并到同一 slot 的测试未产生 Execution。
- Scheduled recovery 测试收到 `tick_once()` 的 `None` 返回值。
- Real API teardown 出现 asyncpg connection 跨事件循环关闭错误。
- Delegation B2 在后台 Worker 已经完成 Delegation 后仍可能尝试再次 Claim。
- B6 诊断测试在固定两轮 dispatch 后观察到仍为 running 的 Delegation。
- 多 Worker Delegation 场景出现 Mock provider HTTP 503，导致部分 Execution 为 failed。

## 2. 根因分析

### 2.1 Scheduler Runtime 生命周期契约缺失

`ScheduledTriggerScheduler.tick_once()` 完成调度循环后没有返回 counters；同时当前 Runtime 文件缺失 `run_forever()` / `stop()` 生命周期入口，而独立 Scheduler entrypoint 已按正式 Service 生命周期调用这两个入口。

这属于生产代码契约不完整，而不是测试断言问题。

修复：恢复 `tick_once()` 的 counters 返回，并补齐 Scheduler 自身轮询生命周期入口；Service Supervisor 仍负责进程生命周期，不由测试 Gate 自动启动或停止服务。

### 2.2 Real API Scheduled Trigger 使用了不正确的时间事实

API 创建 Scheduled Trigger 后，正式 Schedule 的 `next_run_at` 是创建时的当前时间。Real API 测试随后使用 2020 年 synthetic time 调用 `tick_once()`，因此候选自然不会到期。原 `_seed_scheduler_backlog()` 又重新 INSERT Schedule，会违反生产唯一 Schedule 模型并制造第二套持久化事实。

修复：测试只更新 API 创建出的唯一 Schedule，将 `next_run_at` 显式构造为本次测试所需的有效到期事实；不重复创建 Schedule。

### 2.3 Real API 测试跨事件循环复用 AsyncAdaptedQueuePool

Real API 测试使用独立事件循环驱动 SQLAlchemy async 操作。如果测试辅助引擎继续使用默认连接池，连接可能由另一个事件循环创建并在 pytest fixture teardown 中被关闭，最终出现 asyncpg `Future attached to a different loop`。

修复：Real API 测试辅助查询引擎使用 `NullPool`，每个连接只属于当前事件循环；生产数据库连接池保持不变。

### 2.4 Delegation B2 必须先读取 durable 状态再竞争 Claim

真实环境允许后台 Worker 先于测试 Worker 完成 Delegation。若测试在读取 profile 后无条件执行 Claim，生产状态机正确拒绝 `completed` Delegation 再次进入 Worker Runtime。

修复：测试只有在 durable status 为 `pending` 时才尝试 Claim；否则等待已有合法 Worker 收敛。生产 Claim 状态机不放宽。

### 2.5 B6 固定 dispatch 轮次不能等价于 Runtime 完成边界

多 Worker 场景下，测试 Worker、后台 Worker 与 Runtime heartbeat 可以并发推进同一批 durable work。两轮 Claim/Execute 是 dispatch 观察窗口，不是 Runtime terminalization 保证。

修复：在固定 dispatch 后增加有界 terminal drain，并在超时后输出完整 durable facts；不无限延长 timeout，也不启动/停止后台服务。

## 3. 当前仍需本地验证的问题

多 Worker Delegation 中出现 `Mock provider HTTP 503` 的 3 个 failed Execution 仍需要结合下一次本地运行的 target Agent / ModelProfile durable facts 判断是测试环境并发污染、Provider profile 选择问题还是实际 Runtime 错误。当前不修改生产状态机，也不把 failed 强行改判为 completed。

## 4. 验证要求

所有修复必须重新执行：

1. Backend default regression。
2. Alembic upgrade head + current。
3. Tenant-safe Real API Gate。
4. 若 Real API 仍失败，保留失败事实并继续做根因修复，不通过放宽断言掩盖生产问题。

测试 Gate 只检查服务状态，不自动创建、启动、重启或停止 API、Worker、Scheduler、PostgreSQL、Redis。
