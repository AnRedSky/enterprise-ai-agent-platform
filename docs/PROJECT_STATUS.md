# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main` 持续执行 Backend 模块化整改。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler Contract-first + Persistence：**第一版已完成，继续执行 Runtime Gate**。
- 当前：**Backend 模块化整改已完成最终 Closure Gate，主线任务恢复，当前进入 Phase 2.4 Durable Scheduler Runtime Gate。**

## 最新 main 基线

本轮继续直接基于远端 `main`。用户本地已反馈 Closure Gate、API v1、Runtime Boundary、模块重构、依赖边界与 Backend Regression 全部通过；Backend 重构最终静态收口已完成。

本轮 Closure Gate 实际验收结果：

```text
05_backend_refactor_closure_gate.ps1：Backend Refactor Closure Gate completed.
REFACTOR_CLOSURE_IMPORT_OK
```

用户此前实际验收的重构 Gate 结果：

```text
API v1 Module Gate：79 passed；Backend Regression：384 passed, 2 skipped, 35 deselected
Runtime Boundary Gate：79 passed, 215 deselected
Backend Module Refactor Gate：384 passed, 2 skipped, 35 deselected
Dependency Boundary Gate：PASS
Backend default regression：384 passed, 2 skipped, 35 deselected
```

因此本轮不再把 Closure Gate 标记为“等待执行”。重构收口已经具备用户本地实际通过结果。

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

Durable Scheduler 已完成 Contract-first + Persistence 第一版：

- `WorkflowSchedule` / `WorkflowScheduleSlot` 持久化；
- lease / slot 幂等；
- PostgreSQL 原子 claim / release；
- Scheduled Trigger Runtime 已切换到持久化 Scheduler 状态；
- 首版 `misfire=skip` 边界保持明确；
- Scheduler 领域代码已按 `services/workflow_scheduler/` 子模块组织，避免新增第二套调度实现。

**当前唯一下一步：先由开发者本地执行 Scheduler Runtime Gate，确认 Runtime 接入没有回归，再推进 API Contract / 状态可观测性与 tenant isolation / misfire integration。**

## 本地自动化验证流程

```powershell
cd backend

git fetch origin
git reset --hard origin/main
git log -8 --oneline

uv run python -c "from app.main import app; print('APP_IMPORT_OK')"

# 1. 重构最终收口（已通过，后续作为回归 Gate 保留）
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\05_backend_refactor_closure_gate.ps1

# 2. API v1 迁移 Gate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\03_backend_api_v1_module_gate.ps1

# 3. Runtime / Governance 边界 Gate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\04_backend_runtime_boundary_gate.ps1

# 4. 全部模块重构 Gate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1

# 5. 数据库依赖边界 Gate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\02_backend_dependency_boundary_gate.ps1

# 6. Phase 2.4 Scheduler Runtime Gate（当前主线下一步）
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\02_scheduler_runtime_gate.ps1

# 7. Backend default regression
uv run pytest -q
```

本轮未新增 Alembic Migration；重构收口没有数据库结构变更。Phase 2.4 已有持久化 Migration，Scheduler Runtime Gate 会通过 Persistence Gate 实际验证 PostgreSQL 与 Migration。

## 下一执行任务

1. 开发者本地同步最新 `main`。
2. 执行 `scripts/test/integration/02_scheduler_runtime_gate.ps1`。
3. 若 Runtime Gate 暴露问题，只修复 Scheduler canonical 模块，不创建兼容垫片或第二套调度实现。
4. Runtime Gate 通过后，推进 Scheduler API Contract / 状态可观测性。
5. 继续 tenant isolation / misfire integration。
6. 按 Phase 2.4 顺序执行 Tenant Safe Real API、Backend Regression，以及需要时 Frontend / E2E。
7. 根据实际本地结果更新 Phase / Acceptance / Error / Status；未执行结果不得预填“通过”。

模块化目录、职责与迁移规则继续以 `docs/00-architecture/BACKEND_MODULE_ARCHITECTURE.md` 与 `docs/00-architecture/BACKEND_MODULE_MIGRATION_MAP.md` 为准。
