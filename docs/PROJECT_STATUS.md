# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main` 持续执行 Backend 模块化整改。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- Phase 2.4 Durable Scheduler Contract-first + Persistence：**第一版已完成**。
- 当前：**继续执行 Backend 模块化整改，主线任务暂停，必须完成全部既有重构任务后才能恢复主线。**

## 最新 main 基线

本轮继续直接基于远端 `main`。用户本地已反馈 API v1、模块重构、依赖边界、Runtime Boundary 与 Backend Regression 全部通过；当前继续执行全部重构的最终静态收口，不创建兼容分支或兼容垫片。

本轮新增工程变更：

```text
44e2afe test(refactor): add backend refactor closure gate
```

用户本地实际验收结果：

```text
API v1 Module Gate：79 passed
Runtime Boundary Gate：79 passed, 215 deselected
Backend Module Refactor Gate：384 passed, 2 skipped, 35 deselected
Dependency Boundary Gate：PASS
Backend default regression：384 passed, 2 skipped, 35 deselected
```

上述结果均来自用户本地实际执行反馈。新增 `05_backend_refactor_closure_gate.ps1` 尚未由用户本地执行，因此不能记录为通过。

## API v1 重构

API v1 物理模块归位已经完成，并已通过用户本地 Module Gate：

- `app/api/*.py` → `app/api/v1/<domain>/`；
- `main.py` 已切换为 canonical API v1 import；
- 原 `/api/v1/*` 路由前缀保持不变；
- 删除旧 API 文件，不创建兼容转发；
- 各 API 领域包具备中文职责、边界和关键依赖说明；
- 受影响 API Contract / Integration 测试已切换到 canonical API v1 入口；
- Workflow v1 Router 明确 API 层不复制 Workflow / Trigger 领域业务规则。

**状态：API v1 已具备用户本地最终 Gate 结果，等待全量 Refactor Closure Gate 统一收口。**

## Runtime / Governance 当前收口

当前正式 Runtime 仅保留：

- `app/runtime/memory/`：执行期 Memory 上下文构造；
- `app/runtime/model/`：唯一 Model Gateway 执行入口；
- `app/runtime/workflow/`：Workflow 节点执行、重试、超时与熔断。

用户本地已实际执行 `04_backend_runtime_boundary_gate.ps1` 并通过，验证：

- Runtime 根目录不存在旧单文件实现；
- 已删除的 Runtime / Governance 旧 import 未重新出现；
- Runtime 不复制 Model Provider Governance、路由或 Service 实现；
- Runtime 关键模块具备中文“职责 / 边界”说明；
- `ModelGateway` / `WorkflowRuntime` canonical import 可用；
- Runtime targeted unit tests：79 passed，215 deselected。

同时 `app/runtime/model/gateway.py` 的类 docstring 已按开发准则完成中文职责说明。

**状态：Runtime Boundary 已通过用户本地验收，但尚未通过全部重构 Closure Gate，因此仍不能恢复主线。**

## 当前模块重构状态

### 已完成代码迁移 / 已通过对应领域 Gate

- Agent
- Knowledge + Provider
- Memory
- Model + Provider
- Workflow
- Trigger
- Organization
- Observability
- Retrieval Evaluation
- Runtime Query
- Session
- Tool + Tool 技术执行层
- Usage Accounting
- API v1
- Runtime Boundary

### 最终收口中

- 新增 `05_backend_refactor_closure_gate.ps1`：检查旧文件、旧 import、根目录边界、Provider 唯一实现入口、Runtime Governance 重复实现与中文模块职责说明。
- Closure Gate 尚未由用户本地执行。
- Closure Gate 通过后仍需再次执行 Backend Regression，确认最终收口没有回归。
- 仍需更新 Migration Map、Acceptance / Error（仅在实际产生对应事实变化时）并最终确认全部重构领域完成。

**因此当前仍不得恢复 Phase 2.4 主线任务。**

## 本地自动化验证流程

```powershell
cd backend

git fetch origin
git reset --hard origin/main
git log -8 --oneline

uv run python -c "from app.main import app; print('APP_IMPORT_OK')"

# 1. 全部重构最终静态收口 Gate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\05_backend_refactor_closure_gate.ps1

# 2. API v1 迁移 Gate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\03_backend_api_v1_module_gate.ps1

# 3. Runtime / Governance 边界 Gate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\04_backend_runtime_boundary_gate.ps1

# 4. 全部模块重构 Gate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1

# 5. 数据库依赖边界 Gate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\02_backend_dependency_boundary_gate.ps1

# 6. Backend default regression
uv run pytest -q
```

本轮仍未新增 Alembic Migration；目录重构不应改变数据库结构。如数据库 Gate 发现异常，应先记录错误并停止继续迁移。

## 下一执行任务

1. 用户本地同步 `main`，执行 `05_backend_refactor_closure_gate.ps1`。
2. 若 Closure Gate 暴露问题，只修复 canonical 模块边界、唯一实现入口或模块说明，不创建兼容垫片或第二实现。
3. Closure Gate 通过后重新执行 API v1、Runtime Boundary、Module Refactor、Dependency Boundary 与 Backend Regression。
4. 全部 Gate 通过后进行最终旧路径 / 重复实现扫描。
5. 更新 Migration Map、PROJECT_STATUS 与必要的 Acceptance / Error 记录。
6. **全部重构验收完成后，才恢复 Phase 2.4 主线任务。**

模块化目录、职责与迁移规则继续以 `docs/00-architecture/BACKEND_MODULE_ARCHITECTURE.md` 与 `docs/00-architecture/BACKEND_MODULE_MIGRATION_MAP.md` 为准。