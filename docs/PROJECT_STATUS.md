# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler：**Backend 持久化、Runtime、Scheduler API Contract、tenant isolation / misfire、生命周期、真实服务 restart recovery、API/Scheduler 进程解耦已完成开发；Frontend / Browser E2E 上轮已完成实际验证；本轮服务化后完整 Backend / Real API / Restart Gate 需重新执行。**
- Backend 模块化整改：**已完成最终 Closure Gate，不再阻塞主线。**

## 最新 main 基线

当前 `main` 已在历史 Workflow Definition 兼容修复基础上完成 API Service / Scheduler Service 进程职责拆分。

此前 API `lifespan` 会创建 `ScheduledTriggerScheduler`。虽然 PostgreSQL lease / slot 可以保护多实例 ownership 与幂等，但 API 横向扩容会同步增加 Scheduler 后台进程，使 HTTP 生命周期、发布重启与调度生命周期耦合。本轮将 Scheduler 生命周期移出 API，改为独立 `run_scheduler.py` 进程入口。

本轮进一步明确：**服务角色由启动入口决定，而不是由配置开关决定。** `run.py` 永远是 API Service；`run_scheduler.py` 永远是 Scheduler Service。项目不再使用 `SCHEDULER_ENABLED=false` 之类的配置区分两类服务，也不通过该开关把 Scheduler 变成关闭模式。若部署环境不需要 Scheduler，应不启动 Scheduler Service 进程。

## 本轮工程变更

### 服务化进程入口

- `backend/app/entrypoints/__init__.py`
  - 建立独立进程入口模块边界。
- `backend/app/entrypoints/scheduler.py`
  - 负责 Scheduler Service 生命周期编排；不实现 slot / lease / misfire 业务规则。
  - 删除 `scheduler_enabled` 启动拒绝逻辑，确保 Scheduler 入口身份固定。
- `backend/run.py`
  - 明确为 API Service 启动入口。
- `backend/run_scheduler.py`
  - 明确为 Scheduler Service 独立启动入口。
  - 启动信息不再打印 `scheduler_enabled`，避免暗示服务角色由配置切换。
- `backend/app/main.py`
  - 删除 API lifespan 中的 Scheduler 创建、后台 task 与停止逻辑。
  - `/health` 增加 `service=api`，明确 API Service 身份。
- `backend/app/core/config.py`
  - 删除 `scheduler_enabled` 配置 Contract；保留 Scheduler 自身运行参数。

### 测试

- `backend/tests/unit/test_service_entrypoints.py`
  - 验证 API 启动不创建 Scheduler；
  - 验证 Scheduler Service 复用唯一 `ScheduledTriggerScheduler`；
  - 验证 Scheduler Service 的身份不依赖 `SCHEDULER_ENABLED` 配置。

### 架构 / Phase / Acceptance

- `docs/00-architecture/SERVICE_RUNTIME_ARCHITECTURE.md`
  - 明确 API / Scheduler 服务角色由启动入口确定，不使用 `SCHEDULER_ENABLED` 进行角色切换。
- `docs/02-phases/PHASE_2_4.md`
  - 记录 Phase 2.4 服务化拆分及后续 Worker 扩展边界。
- `docs/03-acceptance/PHASE_2_4_ACCEPTANCE.md`
  - 增加服务职责、启动方式与本地验收流程。

## 当前服务架构

```text
API Service
    backend/run.py
    └── FastAPI / HTTP / Auth / API Router

Scheduler Service
    backend/run_scheduler.py
    └── ScheduledTriggerScheduler
        ├── PostgreSQL lease
        ├── schedule slot
        ├── misfire
        └── WorkflowTriggerService dispatch

Worker Service
    └── 后续扩展，当前不实现空壳
```

API 与 Scheduler 共享正式 Domain / Runtime / Infrastructure，但不共享进程生命周期。Worker 后续必须在 Task Contract、Queue/Broker、retry、lease、DLQ、cancellation 与 tenant boundary 明确后再实施。

## 当前 Gate 状态

```text
服务职责边界单测                                      ↓ 本轮待执行
Backend default regression                            ↓ 本轮待重新执行
Tenant Safe Real API Gate                             ↓ 本轮待重新执行
Scheduler Restart Acceptance                          ↓ 本轮待重新执行
Frontend Regression Gate                              ↓ 服务化后按范围重新确认
Workflow Trigger Browser Gate                         ↓ 服务化后按范围重新确认
Phase 2.4 Acceptance 汇总                             ↓
```

上轮开发者实际反馈：

```text
Backend default regression: 397 passed, 3 skipped, 36 deselected
Tenant Safe Real API Gate: 35 passed
Frontend Regression: 79 passed + production build
Workflow Trigger Browser E2E: 1 passed
```

以上属于上一轮实际结果，不代表本轮服务化拆分已经通过。

## 本轮运行方式

API Service：

```powershell
cd backend
uv run python run.py
```

Scheduler Service：

```powershell
cd backend
uv run python run_scheduler.py
```

两个入口的服务身份固定：

```text
run.py           → API Service
run_scheduler.py → Scheduler Service
```

API Service 不再自动启动 Scheduler。开发机如果同时需要 HTTP 与 Scheduled Trigger，必须显式启动两个进程。若只需要 API，则只启动 `run.py`；若只需要 Scheduler，则只启动 `run_scheduler.py`，不需要修改任何配置开关。

## 当前禁止事项

- 不创建第二套 Scheduler / Repository / Provider / Execution / slot key 实现；
- 不通过修改测试断言掩盖生产 Runtime metadata Contract；
- 不使用 JSON fixture 替代真实 PostgreSQL Scheduler 状态；
- 不创建兼容垫片、旧入口转发或功能分支；
- 不把 GitHub Actions 结果当作本地开发 Gate 或验收结果；
- Scheduler Restart Acceptance 不得让测试自身启动的多个 Scheduler worker 共享同一目标 slot；
- 历史 Definition 兼容不得扩大为任意非法节点自动转换；只有可确定语义的历史空节点允许受控兼容；
- API Service 不得恢复内嵌 Scheduler；Scheduler 必须保持独立进程入口；
- **不得使用 `SCHEDULER_ENABLED` 或等价配置开关区分 API Service 与 Scheduler Service；服务角色必须由启动入口固定确定；**
- Worker Service 在 Task Contract 与 Queue/Broker 等基础 Contract 未明确前不得创建空壳实现。
