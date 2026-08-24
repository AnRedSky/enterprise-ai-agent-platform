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

本轮基于远端 `main` 最新提交 `5887c5c fix(refactor): complete workflow and dependency gate cleanup` 继续执行，不创建兼容分支或兼容垫片。

用户本地基线验证结果：

```text
APP_IMPORT_OK
Module Refactor Gate: 384 passed, 2 skipped, 35 deselected
Dependency Boundary Gate: PASS
Backend default regression: 384 passed, 2 skipped, 35 deselected
```

以上为用户本地实际反馈，本轮 API v1 代码迁移后的新验证结果尚未执行，不预填通过。

## 本轮 API v1 重构

已完成 API 物理模块归位：

- `app/api/*.py` → `app/api/v1/<domain>/`；
- `main.py` 已切换为 canonical API v1 import；
- 原 `/api/v1/*` 路由前缀保持不变；
- 删除旧 API 文件，不创建兼容转发；
- 为 API 根包、v1 包及各领域包补充中文职责、边界和关键依赖说明；
- 新增 `scripts/test/module-refactor/03_backend_api_v1_module_gate.ps1`，负责旧 API 路径、模块说明、应用 import、API Contract 与 Backend Regression 验证。

**状态：代码迁移完成，待本地 Gate / Regression 实际验收。**

## 当前模块重构状态

### 已完成代码迁移 / 待全量最终 Gate

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

- 全部领域 Module Refactor Gate 最终全量验收
- 全量旧 import 搜索确认 0
- 全部重构领域重复实现审查
- Runtime 其他领域边界审查
- Governance 领域其余职责收敛

**因此当前仍不得恢复 Phase 2.4 主线任务。**

## 文档与错误记录

本轮未产生新的已确认工程错误；API v1 迁移后的测试结果待本地执行后，如发现问题，再按 `docs/04-errors/` 规则记录。

## 本地自动化验证流程

```powershell
cd backend

git fetch origin
git reset --hard origin/main
git log -8 --oneline

uv run python -c "from app.main import app; print('APP_IMPORT_OK')"

# 1. API v1 迁移 Gate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\03_backend_api_v1_module_gate.ps1

# 2. 全部模块重构 Gate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1

# 3. 数据库依赖边界 Gate
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\02_backend_dependency_boundary_gate.ps1

# 4. Backend default regression
uv run pytest -q
```

本轮 API 目录重构未新增 Alembic Migration；如果后续验证发现数据库状态异常，应先记录错误并停止继续迁移，不得为了目录整改修改数据库结构。

## 下一执行任务

1. 本地同步本轮最新 `main`。
2. 执行 API v1 Module Gate，确认旧 `app.api.<module>` 路径为 0。
3. 执行 Module Refactor Gate、Dependency Boundary Gate 与 Backend Regression。
4. 根据真实测试反馈继续修复 Runtime / Governance / 重复实现问题。
5. 全部重构领域最终 Gate 通过后，才能恢复 Phase 2.4 主线任务。

模块化目录、职责与迁移规则继续以 `docs/00-architecture/BACKEND_MODULE_ARCHITECTURE.md` 与 `docs/00-architecture/BACKEND_MODULE_MIGRATION_MAP.md` 为准。
