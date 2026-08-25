# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**API / Scheduler 进程解耦已完成；独立 Scheduler restart acceptance 已通过。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**代码实现完成；Worker ownership fencing、Tenant Safe Real API、Backend Regression、Scheduler/Worker Recovery Acceptance 已完成开发者本地验证。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

当前远端 `main`：`85164f0 fix(worker): make consistency gate independent of caller directory`。

本轮前置修复：`b84a088 fix(worker): make runtime consistency diagnostic directly executable`。

```text
API Service       run.py
Scheduler Service run_scheduler.py
Worker Service    run_worker.py
```

服务角色由启动入口固定确定，不使用 `SCHEDULER_ENABLED` / `WORKER_ENABLED` 切换角色。

## 当前执行链

```text
API Service
    ↓ HTTP
Workflow / Trigger Domain
    ↓
Scheduler Service
    ├── schedule / lease / slot / misfire
    └── create pending WorkflowExecution
              ↓ PostgreSQL
Worker Service
    ├── claim pending Execution
    ├── worker lease
    ├── ownership fencing
    └── WorkflowExecutionService.run()
              ↓
WorkflowRuntime
```

核心职责：**Scheduler 负责“什么时候执行”，Worker 负责“执行什么”。**

## 开发者本轮实际验收结果

### 1. Worker ownership targeted Unit

```text
7 passed in 0.92s
```

### 2. Migration

```text
uv run alembic upgrade head
0031_usage_provider_lifecycle (head)
```

### 3. Tenant Safe Real API

连续两次实际执行：

```text
35 passed in 61.53s
35 passed in 65.24s
```

### 4. Backend Regression Gate

```text
411 passed, 3 skipped, 36 deselected in 29.70s
Migration head verified: 0031_usage_provider_lifecycle
Tenant Safe Real API: 35 passed in 57.33s
[PASS] Backend regression gate completed.
```

### 5. Scheduler / Worker Recovery Acceptance

开发者此前实际反馈：

```text
1 passed in 9.55s
[PASS] Scheduler / Worker recovery acceptance completed.
```

以上结果均来自开发者本地实际执行，不以 GitHub Actions 替代本地验收。

## Worker 手工运行日志分析

开发者直接执行 `uv run python run_worker.py` 时观察到：

```text
503 Circuit Breaker is open
404 Mock provider HTTP 404
504 Retry backoff exceeds workflow deadline
409 Node 不允许从 running 到 running
```

其中 `503 / 404 / 504` 均对应已有负向业务路径；`409 running → running` 仍必须保持禁止，不能放宽 Node 状态机。

为定位 `409` 是否来自遗留持久化不一致，新增只读诊断：

```text
backend/scripts/dev/inspect_worker_runtime_consistency.py
backend/scripts/dev/worker_runtime_consistency.ps1
```

本轮进一步修复了诊断入口的直接执行问题：

- Python 诊断脚本显式加入 `backend` 根目录到 `sys.path`，不再依赖当前工作目录碰巧能解析 `app` 包；
- PowerShell Gate 根据 `$PSScriptRoot` 定位 `backend`，调用者不必先切换到 `backend` 目录；
- 两个入口仍保持只读，不启动、停止或重启 API / Scheduler / Worker。

## 当前剩余工作

1. 开发者重新执行 Worker Runtime 一致性诊断，确认是否存在 `pending + running Node` 遗留数据。
2. 若存在，记录具体 Execution ID / Worker owner / attempt，并单独分析其来源；不得自动 resume。
3. 若不存在，则将 `409 running → running` 归类为历史异常日志或测试场景残留，不修改生产 Node 状态机。
4. 诊断通过后，再根据实际数据库结果决定是否需要增加针对遗留状态来源的确定性回归测试；当前不修改 Node 状态机。
5. Frontend / Browser E2E 按实际 API Contract 影响范围独立执行，不并入 Backend Gate。

## 当前禁止事项

- 不恢复 API 内嵌 Scheduler；
- 不让 Scheduler 直接执行 Workflow Runtime；
- 不创建第二套 Execution Service / Runtime / Provider；
- 不通过 JSON fixture 替代真实 PostgreSQL Task Contract；
- 不通过 Mock Runtime 作为 Real Acceptance；
- 不加入 running Execution 自动 resume；
- 不创建 MQ/Kafka/Celery 作为当前阶段必要依赖；
- 不创建功能分支，所有开发直接基于并提交 `main`；
- 不允许测试 Gate 自动控制 API / Scheduler / Worker 生命周期；
- 不放宽 `running → running` Node 状态转换来掩盖重复 Runtime。

## 本轮文档与错误记录

- `docs/PROJECT_STATUS.md`
- `docs/02-phases/PHASE_2_5.md`
- `docs/04-errors/2026-08-25-worker-runtime-running-node-consistency.md`

