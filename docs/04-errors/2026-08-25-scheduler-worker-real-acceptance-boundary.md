# Scheduler / Worker Real Acceptance 的本地进程边界与 Execution running 问题

## 发生时间

2026-08-25

## 问题

本轮本地验收出现两类阻塞：

1. Tenant Safe Real API Gate 中，Scheduler 产生的 recovery Execution 已持久化，但在测试等待窗口内仍为 `running`。
2. Scheduler / Worker Restart Acceptance 检测到多个已有 API、Scheduler、Worker 进程并提前退出。

## 分析

### 1. `running` 状态不能简单视为 Scheduler 问题

当前服务边界已经明确：

```text
Scheduler → pending WorkflowExecution → PostgreSQL → Worker → WorkflowExecutionService → WorkflowRuntime
```

因此 Scheduler 创建 Execution 后，`running` 表示 Worker 已经进入 Workflow Execution 状态机，而不是 Scheduler 仍在执行 Workflow。

本轮 observed `running` 的关键诊断字段必须包括：

- `worker_owner`
- `worker_lease_expires_at`
- `worker_attempt`
- `started_at`
- `ended_at`
- `error_code`
- `error_message`

后续 Real API Gate 应根据这些字段判断是 Worker 未消费、Worker 执行卡住，还是 Runtime 本身失败。

### 2. Worker 必须有明确的单次执行上界

此前 Worker 在 claim 后直接等待 `WorkflowExecutionService.run()` 返回。即使 Runtime 自身具有 workflow/node timeout，Worker 层仍缺少最后一道进程级执行上界。

本轮修复在 Worker 中增加：

- 读取 Workflow Runtime timeout；
- 加固定执行宽限时间；
- 执行上界不得超过 Worker lease；
- 超时且 Execution 仍为 `running` 时写入 `WORKER_EXECUTION_TIMEOUT` 并结束任务；
- terminal Execution 继续清理 Worker owner / lease。

该逻辑不是自动 resume `running Execution`，也不改变当前状态机，只负责防止单个 Worker 协程无限占用。

### 3. Restart Acceptance 不应把 API / Worker 与 Scheduler 混为一个进程冲突集合

API Service 是 HTTP 管理入口，可以与 Acceptance 的临时 API 共存，只要使用独立端口。

Worker Service 是 PostgreSQL Execution 消费者，允许已有 Worker 参与任务竞争；其 claim 使用 PostgreSQL 行锁与 lease，不应因为存在一个本地 Worker 就直接阻断 Real API Gate。

Scheduler 则不同：多个 Scheduler 会竞争同一 `WorkflowSchedule` 的 lease，并可能在测试预期的“停止 Scheduler”阶段继续推进 schedule，因此 Restart Acceptance 必须独占 Scheduler。

因此 Acceptance 脚本调整为：

- 仅禁止已有 `run_scheduler.py`；
- 允许已有 API Service；
- 允许已有 Worker Service；
- 临时 API 继续使用随机端口；
- 独立 Scheduler / Worker 仍由 pytest 生命周期负责启动和停止。

## 验证要求

```powershell
cd backend
uv run pytest -q tests/unit/test_workflow_worker.py
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_backend_regression_gate.ps1
```

Scheduler / Worker Restart Acceptance 单独执行时，必须先确保没有其他 `run_scheduler.py` 进程：

```powershell
Get-CimInstance Win32_Process | Where-Object {
  $_.CommandLine -and $_.CommandLine -match "run_scheduler\.py"
} | Select-Object ProcessId,CommandLine
```

不要通过修改 API/Scheduler/Worker 的正式进程边界来规避测试冲突。
