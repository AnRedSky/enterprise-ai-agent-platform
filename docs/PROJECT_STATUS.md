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

当前远端 `main`：`c808d86 docs(worker): record consistency diagnostic entrypoint fix`。

本轮 Worker 恢复整改基线：在上述 main 基础上增加 orphaned running Node recovery，不修改 Node 状态机合法转换。

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
    ├── recover orphaned running Node
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

## 当前 Worker 整改

`running → running` 不是合法状态转换，不通过放宽状态机解决。当前 Worker 在正式进入 Runtime 前增加恢复边界：当已 claim 的 `pending Execution` 存在遗留 `running Node` 时，先将其以 `WORKER_RECOVERY_INTERRUPTED` 转为 `failed`，随后由现有 WorkflowRuntime retry policy 决定是否重新执行。

对应实现：

```text
backend/app/services/workflow_worker/runtime.py
WorkflowWorker._recover_orphaned_running_nodes()
```

对应测试：

```text
backend/tests/unit/test_workflow_worker.py
```

对应错误记录：

```text
docs/04-errors/WORKER_RUNNING_NODE_RECOVERY.md
```

## 当前剩余工作

1. 开发者在最新 main 上执行 Worker targeted tests，确认恢复逻辑实际通过。
2. 执行 Backend Regression Gate，确认 Worker 恢复代码没有破坏既有 ownership fencing、Runtime、API 与 migration 质量门禁。
3. 执行只读 Worker Runtime consistency diagnostic，确认数据库当前是否仍存在 `pending + running Node` 遗留状态；诊断不得自动修改数据。
4. 执行实际 Worker 生命周期 / Recovery Acceptance，验证旧 Worker 失去 ownership 后不能继续推进 Execution。
5. Frontend / Browser E2E 按实际 API Contract 影响范围独立执行，不并入 Backend Gate。

## 当前禁止事项

- 禁止把 `running → running` 改成合法状态转换。
- 禁止通过自动 reset 数据库来掩盖 Worker 恢复问题。
- 禁止新增平行 Workflow Runtime 或第二套 Provider。
- 禁止用 GitHub Actions 结果替代开发者本地实际测试结果。
