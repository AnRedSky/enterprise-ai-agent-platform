# Scheduler Recovery Acceptance：Trigger 创建与 Schedule 初始化竞态

## 1. 发生现象

本地真实 Scheduler/Worker Recovery Acceptance 在创建 Scheduled Trigger 后立即执行 `workflow_schedules` 历史 slot 回拨，偶发或稳定出现：

```text
AssertionError: Scheduler 状态回拨失败，trigger_id=...
```

对应 SQL 的 `UPDATE workflow_schedules ... WHERE trigger_id = :trigger_id` 返回 `rowcount = 0`，说明测试执行到回拨阶段时，Scheduler 持久化 Schedule 尚未创建。

## 2. 根因

Scheduled Trigger 创建与 Scheduler Schedule 初始化属于两个独立事务。Trigger API 只负责持久化 `WorkflowTrigger`；`workflow_schedules` 由独立 Scheduler Runtime 首次轮询时通过 `WorkflowSchedulerRepository.ensure_schedule()` 懒初始化。

因此：

```text
POST /triggers
    ↓
WorkflowTrigger 已提交
    ↓
Scheduler 尚未完成下一次 tick
    ↓
测试立即 UPDATE workflow_schedules
    ↓
rowcount = 0
```

这不是 PostgreSQL 数据丢失，也不是 Scheduler 服务未启动，而是验收脚本错误地假设了跨进程异步初始化已经同步完成。

## 3. 修复

在真实验收测试中增加 `_wait_for_schedule()`：

1. Trigger 继续通过真实 HTTP API 创建；
2. 不启动、停止或重启任何服务；
3. 通过真实 PostgreSQL 查询等待 Scheduler 创建 `workflow_schedules`；
4. Schedule 行出现后再执行历史 slot 回拨；
5. 超过 15 秒仍未出现则明确报告 Scheduler 未完成初始化，而不是误报为状态回拨失败。

该等待覆盖 Scheduler 正常轮询周期，同时保持服务生命周期完全由开发者手动管理。

## 4. 影响范围

仅影响 Scheduler/Worker Recovery Acceptance 的测试时序，不改变生产 Scheduler、Worker、Trigger、Schedule 或 Execution 业务逻辑。

## 5. 防回归验证

必须执行：

```powershell
cd backend
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\02_run_scheduler_restart_acceptance.ps1
```

其中 Real API / Scheduler Recovery Acceptance 的前置 API、Scheduler、Worker 服务必须由开发者手动启动；测试脚本不得启动、停止或重启这些服务。
