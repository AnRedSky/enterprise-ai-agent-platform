# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**；本轮补充修复历史 Usage Record 与 Model Provider/Profile 生命周期冲突。
- Phase 2.4 Durable Scheduler：**API / Scheduler 进程解耦已完成；上一轮独立 Scheduler restart acceptance 已通过。**
- Phase 2.5 Scheduler → Worker Execution Decoupling：**代码实现完成；ownership fencing 修复与 Scheduler Recovery Acceptance 已完成本地反馈验证；本轮继续处理 Real API Gate 的 Worker 竞争竞态与 Model Provider 历史用量生命周期阻塞。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

当前远端 `main` 已完成：

```text
API Service
    run.py

Scheduler Service
    run_scheduler.py

Worker Service
    run_worker.py
```

服务角色由启动入口固定确定，不使用 `SCHEDULER_ENABLED` / `WORKER_ENABLED` 等配置开关切换角色。

## 当前执行链

```text
API Service
    ↓ HTTP
Workflow / Trigger Domain
    ↓
Scheduler Service
    ├── schedule
    ├── lease
    ├── slot
    ├── misfire
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

核心职责：

> **Scheduler 负责“什么时候执行”，Worker 负责“执行什么”。**

## 本轮最新反馈与修复

### 1. Scheduler Recovery Acceptance

开发者本地反馈：

```text
1 passed in 11.90s
[PASS] Scheduler / Worker recovery acceptance completed.
```

此前 `workflow_schedules` 回拨 `rowcount = 0` 的竞态已经通过 `fcf3326` 增加 Scheduler Schedule 初始化等待解决。该 Gate 不启动、停止或重启服务。

### 2. Backend default regression

开发者本地反馈：

```text
409 passed, 3 skipped, 36 deselected
```

当前 main 基线进一步反馈为：

```text
409 passed, 3 skipped, 36 deselected
```

本轮新增代码尚未在开发者本地重新执行完整 Backend Gate，因此不能把上述结果视为本轮最终验收结果。

### 3. Tenant Safe Real API bootstrap 竞态

开发者本地反馈发现：Real API bootstrap 创建 `pending` Execution 后，独立 Worker 可能先于 bootstrap 的 `/run` 请求抢占并完成该 Execution，导致：

```text
POST /workflows/executions/<id>/run
-> expected HTTP 404, got 409
只有 pending Execution 可以 Run
```

该 409 在当前 Scheduler → Worker 架构下可能是合法的并发竞争结果，不应被 Real API Gate 当作随机失败。本轮已修改 bootstrap：

- `/run` 保持原有 Contract，不放宽生产状态机；
- 若 `/run` 成功，则继续验证真实 HTTP / PostgreSQL 持久化结果；
- 若 `/run` 返回明确的 `只有 pending Execution 可以 Run`，则认为 Worker 已合法抢占，改为轮询真实 Execution 直到终态；
- 只接受与 Fixture Contract 一致的终态和错误码；
- 超时、其他 409 或其他 HTTP 错误仍直接失败。

### 4. Model Provider / Usage Record 生命周期

开发者本地 Real API Governance 测试在 Profile 删除后继续删除 Provider 时出现：

```text
500 Internal Server Error
```

根因是 `model_usage_records.provider_id` 仍使用：

```text
ON DELETE RESTRICT
NOT NULL
```

而 Usage Record 已经保存独立的 `model_type / model_name / pricing / cost` 历史快照，因此 Provider 删除不应阻塞历史用量生命周期。本轮新增：

```text
0031_usage_provider_lifecycle
```

将 `model_usage_records.provider_id` 调整为可空，并使用：

```text
ON DELETE SET NULL
```

删除 Provider 后历史 Usage Record 保留，仅解除当前 Provider 引用。

### 5. Worker `running → running`

此前日志中的：

```text
409: Node 不允许从 running 到 running
```

不作为本轮状态机放宽依据。当前设计仍禁止 `running → running`，也不偷偷增加 running Execution 自动 resume。ownership fencing 通过 Worker lease 阻断 stale consumer；若后续再次出现该日志，应继续按 Worker owner / lease / Node 状态转换边界定位。

## 当前 Gate 状态

本轮代码修复后必须重新执行：

```text
① Worker ownership fencing Unit
② Worker Unit
③ Backend default regression
④ Database migration/head
⑤ Tenant Safe Real API
⑥ Scheduler + Worker Recovery Acceptance
⑦ Frontend Regression（受范围影响时）
⑧ Workflow Trigger Browser E2E（受范围影响时）
```

**本文件不预填本轮修复后的测试通过结果。**

开发者此前已实际反馈：

```text
Backend default regression: 409 passed, 3 skipped, 36 deselected
Tenant Safe Real API: 33 passed, 2 failed
Scheduler / Worker Recovery Acceptance: 1 passed
```

上述结果只记录修复前的实际事实；不能作为本轮修复后的验收结果。

## 本地服务前置条件

### API Service

```powershell
cd backend
uv run python run.py
```

### Scheduler Service

```powershell
cd backend
uv run python run_scheduler.py
```

### Worker Service

```powershell
cd backend
uv run python run_worker.py
```

完整 Scheduled Workflow 执行链需要 Scheduler + Worker；Real HTTP API Gate 需要 API + Worker；Scheduler Recovery Acceptance 需要 Scheduler + Worker，并由脚本验证服务已经存在。

**测试脚本绝不启动、停止或重启上述服务。**

## 当前禁止事项

- 不恢复 API 内嵌 Scheduler；
- 不使用 `SCHEDULER_ENABLED` / `WORKER_ENABLED` 区分服务角色；
- 不让 Scheduler 直接执行 Workflow Runtime；
- 不创建第二套 Execution Service / Runtime / Provider；
- 不通过 JSON fixture 替代真实 PostgreSQL Task Contract；
- 不通过 Mock Runtime 作为 Real Acceptance；
- 不在本阶段偷偷加入 running Execution 自动 resume；
- 不创建 MQ/Kafka/Celery 等 Broker 作为当前阶段必要依赖；
- 不创建功能分支，所有开发直接基于并提交 `main`；
- 不允许测试 Gate 自动控制本地 API / Scheduler / Worker 生命周期。

## 文档记录

本轮同步维护：

- `docs/00-architecture/SERVICE_RUNTIME_ARCHITECTURE.md`
- `docs/02-phases/PHASE_2_5.md`
- `docs/03-acceptance/PHASE_2_5_ACCEPTANCE.md`
- `docs/PROJECT_STATUS.md`
- `docs/04-errors/2026-08-25-worker-node-running-concurrent-owner.md`
- `docs/04-errors/2026-08-25-real-api-governance-profile-lifecycle.md`
- `docs/04-errors/2026-08-25-real-api-worker-claim-race-and-provider-lifecycle.md`
