# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main`。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler Contract-first + Persistence：**第一版已完成，Runtime Gate 已由开发者本地实际通过，当前推进 Scheduler API Contract / 状态可观测性**。
- 当前：**Backend 模块化整改已完成最终 Closure Gate，主线任务恢复，当前进入 Phase 2.4 Scheduler API Contract / 状态可观测性。**

## 最新 main 基线

本轮继续直接基于远端 `main`。用户本地已反馈 Closure Gate、API v1、Runtime Boundary、模块重构、依赖边界、Scheduler Persistence、Scheduler Runtime 与 Backend Regression 均通过。

重构最终收口实际验收结果：

```text
05_backend_refactor_closure_gate.ps1：Backend Refactor Closure Gate completed.
REFACTOR_CLOSURE_IMPORT_OK
```

Phase 2.4 Runtime Gate 实际验收结果：

```text
Scheduler Runtime targeted tests：4 passed
Scheduler Persistence Gate：Alembic current = 0028_durable_scheduler_persistence (head)
Scheduler contract targeted tests：13 passed
Scheduler repository PostgreSQL integration：2 passed
Backend default regression：384 passed, 2 skipped, 35 deselected
```

因此当前不再把模块化重构或 Scheduler Runtime 标记为阻塞项。

## Backend 模块化重构收口

API v1、Runtime Boundary 以及各领域 Service / Runtime / Provider 迁移已经完成；最终 Closure Gate 已确认：

- 旧扁平领域实现文件不存在；
- API / Runtime 旧 import 路径不存在；
- `services` / `runtime` 根目录没有重新堆放领域实现；
- Provider 技术适配保持 `app/infrastructure/providers/` 唯一正式入口，并排除 ORM `app/models` 与 canonical Model Provider Service 的合理命名；
- Runtime 没有重复 Model Provider Governance / 路由实现；
- 正式领域包具备中文“职责 / 边界”说明；
- canonical 应用入口与 Runtime 导出可正常导入。

**状态：Backend 模块化重构全部 Closure Gate 已完成，不再阻塞主线。**

## Phase 2.4 当前推进

Durable Scheduler 已完成 Contract-first + Persistence 第一版，并已完成本地 Runtime Gate：

- `WorkflowSchedule` / `WorkflowScheduleSlot` 持久化；
- lease / slot 幂等；
- PostgreSQL 原子 claim / release；
- Scheduled Trigger Runtime 已切换到持久化 Scheduler 状态；
- 首版 `misfire=skip` 边界保持明确；
- Scheduler 领域代码已按 `services/workflow_scheduler/` 子模块组织，避免新增第二套调度实现；
- 新增 Scheduled Trigger Scheduler 状态只读 API Contract，直接复用 `WorkflowSchedulerRepository`，不复制调度规则。

当前 API 状态查询入口：

```text
GET /api/v1/workflows/{workflow_id}/triggers/{trigger_id}/schedule
```

该接口只读返回持久化调度状态，包括 enabled/status、timezone、next/last run、last execution、lease 是否有效、misfire policy 等，不暴露 Scheduler worker owner。

## 本轮下一步

1. 本地执行 Scheduler API Contract Gate；
2. 若 API Contract 暴露问题，只修复 canonical Workflow API / Scheduler Repository，不创建兼容垫片或第二套调度实现；
3. API Contract 通过后推进 tenant isolation / misfire integration；
4. 再执行 Tenant Safe Real API Gate 与 Backend Regression；
5. 根据实际本地结果更新 Phase、Acceptance、Status 与必要 Error 记录。

## 本地自动化验证流程

```powershell
cd backend

git fetch origin
git reset --hard origin/main
git log -8 --oneline

uv run python -c "from app.main import app; print('APP_IMPORT_OK')"

# 1. 重构最终收口回归
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\05_backend_refactor_closure_gate.ps1

# 2. Scheduler Runtime Gate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\02_scheduler_runtime_gate.ps1

# 3. Scheduler API Contract Gate（本轮新增）
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\03_scheduler_api_contract_gate.ps1

# 4. Backend default regression
uv run pytest -q
```

本轮未新增 Alembic Migration；Scheduler API Contract 只读取既有 `0028_durable_scheduler_persistence` 持久化结构。
