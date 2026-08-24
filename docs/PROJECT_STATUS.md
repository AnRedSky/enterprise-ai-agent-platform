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

本轮继续直接基于远端 `main`。用户本地已反馈 API v1、模块重构、依赖边界与 Backend Regression 全部通过；当前继续推进 Runtime / Governance 边界最终收口，不创建兼容分支或兼容垫片。

本轮新增工程变更：

```text
3703673 test(refactor): add runtime boundary gate
442f40b fix(refactor): localize runtime gateway docstring
82f1b40 docs(refactor): define runtime boundary gate and ownership
```

用户本地真实 API v1 / 模块重构验收结果：

```text
API v1 Module Gate：79 passed
Backend Module Refactor Gate：384 passed, 2 skipped, 35 deselected
Dependency Boundary Gate：PASS
Backend default regression：384 passed, 2 skipped, 35 deselected
```

上述结果来自用户本地实际执行反馈，不代表本轮新增 Runtime Boundary Gate 已经在用户本地执行；新增 Gate 必须单独执行后才能记录为通过。

## API v1 重构

API v1 物理模块归位已经完成，并已通过用户本地 Module Gate：

- `app/api/*.py` → `app/api/v1/<domain>/`；
- `main.py` 已切换为 canonical API v1 import；
- 原 `/api/v1/*` 路由前缀保持不变；
- 删除旧 API 文件，不创建兼容转发；
- 各 API 领域包具备中文职责、边界和关键依赖说明；
- 受影响 API Contract / Integration 测试已切换到 canonical API v1 入口；
- Workflow v1 Router 明确 API 层不复制 Workflow / Trigger 领域业务规则。

**状态：API v1 Gate 已由用户本地反馈通过，后续只接受全量最终 Gate 对其进行最终确认。**

## Runtime / Governance 当前收口

Migration Map 当前将 Runtime 标记为“边界收口中”。当前正式 Runtime 仅保留：

- `app/runtime/memory/`：执行期 Memory 上下文构造；
- `app/runtime/model/`：唯一 Model Gateway 执行入口；
- `app/runtime/workflow/`：Workflow 节点执行、重试、超时与熔断。

新增 `backend/scripts/test/module-refactor/04_backend_runtime_boundary_gate.ps1`，专门验证：

- Runtime 根目录不存在旧单文件实现；
- 已删除的 Runtime / Governance 旧 import 不得重新出现；
- Runtime 不复制 Model Provider Governance、路由或 Service 实现；
- Runtime 关键模块具备中文“职责 / 边界”说明；
- `ModelGateway` / `WorkflowRuntime` canonical import 可用；
- Runtime targeted unit tests 可重复执行。

同时修正 `app/runtime/model/gateway.py` 中英文类 docstring，使其符合开发准则第 21、25 条的中文说明要求。

**状态：代码与 Gate 已准备完成，等待用户本地执行 Runtime Boundary Gate；在执行前不得将 Runtime / Governance 标记为迁移完成。**

## 当前模块重构状态

### 已完成代码迁移 / 已具备最终 Gate

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

### 仍需最终收口

- Runtime Boundary Gate 实际本地验收
- 全部领域 Module Refactor Gate 最终全量验收
- 全量旧 import 搜索确认 0
- 全部重构领域重复实现最终审查
- Governance 领域其余职责收敛确认

**因此当前仍不得恢复 Phase 2.4 主线任务。**

## 本地自动化验证流程

```powershell
cd backend

git fetch origin
git reset --hard origin/main
git log -8 --oneline

uv run python -c "from app.main import app; print('APP_IMPORT_OK')"

# 1. API v1 迁移 Gate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\03_backend_api_v1_module_gate.ps1

# 2. Runtime / Governance 边界 Gate（本轮新增）
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\04_backend_runtime_boundary_gate.ps1

# 3. 全部模块重构 Gate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1

# 4. 数据库依赖边界 Gate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\02_backend_dependency_boundary_gate.ps1

# 5. Backend default regression
uv run pytest -q
```

本轮仍未新增 Alembic Migration；如果后续验证发现数据库状态异常，应先记录错误并停止继续迁移，不得为了目录整改修改数据库结构。

## 下一执行任务

1. 用户本地同步最新 `main`，确认包含 Runtime Boundary Gate 与 Gateway docstring 修复。
2. 执行 Runtime Boundary Gate，重点观察旧 Runtime / Governance import、重复实现和模块说明检查。
3. 继续执行 API v1 Module Gate、Module Refactor Gate、Dependency Boundary Gate 与 Backend Regression，确认新增变更没有回归。
4. 若 Runtime Boundary Gate 暴露问题，只修复 canonical 模块边界，不创建兼容垫片或第二实现。
5. Runtime / Governance 最终收口后，再执行一次全量旧路径 / 重复实现扫描并更新 Migration Map、PROJECT_STATUS。
6. 全部重构领域最终 Gate 通过后，才能恢复 Phase 2.4 主线任务。

模块化目录、职责与迁移规则继续以 `docs/00-architecture/BACKEND_MODULE_ARCHITECTURE.md` 与 `docs/00-architecture/BACKEND_MODULE_MIGRATION_MAP.md` 为准。