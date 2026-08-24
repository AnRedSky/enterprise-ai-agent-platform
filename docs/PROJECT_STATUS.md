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

本轮继续直接基于远端 `main`。截至当前最新提交，API v1 重构相关测试旧 import 又发现一组 Workflow Trigger 动态 import 残留，已继续修复并补充模块职责说明；不创建兼容分支或兼容垫片。

本轮新增修复提交：

```text
c4dea56 fix(refactor): update scheduled trigger contract import
5f8dac2 fix(refactor): update webhook contract import
271a898 refactor(api): document workflow v1 router responsibility
da1349d docs(errors): record remaining workflow API legacy imports
```

用户本地真实反馈：

```text
API v1 Module Gate：发现 app.api.workflows 仍被两个 API Contract 测试动态引用
Backend Regression：2 failed, 382 passed, 2 skipped, 35 deselected
```

本轮已将这两个测试切换到 `app.api.v1.workflows.router`，并为 Workflow v1 Router 补充中文职责、边界与关键依赖说明。

**本轮修复后的 API v1 Module Gate / Backend Regression 尚未在用户本地重新执行，不预填通过。**

## 本轮 API v1 重构

已完成 API 物理模块归位：

- `app/api/*.py` → `app/api/v1/<domain>/`；
- `main.py` 已切换为 canonical API v1 import；
- 原 `/api/v1/*` 路由前缀保持不变；
- 删除旧 API 文件，不创建兼容转发；
- 为 API 根包、v1 包及各领域包补充中文职责、边界和关键依赖说明；
- 新增 `scripts/test/module-refactor/03_backend_api_v1_module_gate.ps1`，负责旧 API 路径、模块说明、应用 import、API Contract 与 Backend Regression 验证；
- 修复受影响 API Contract / Integration 测试的旧 import，测试直接使用 canonical API v1 入口；
- Workflow v1 Router 已补充模块级职责说明，明确 API 层不复制 Workflow / Trigger 领域业务规则。

**状态：代码与测试 import 已继续收口，待本地 Gate / Regression 实际验收。**

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

本轮继续更新工程错误记录：

- `docs/04-errors/2026-08-24-api-v1-legacy-imports.md`：补充 Workflow Trigger 测试残留旧 API import 的第二次真实反馈与修复。

本轮修复后的测试结果待用户本地实际执行后补充；禁止预填“通过”。

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

1. 本地同步最新 `main`，确认包含本轮 Workflow Trigger 测试 import 修复。
2. 执行 API v1 Module Gate，确认旧 `app.api.<module>` 路径为 0。
3. 执行 Module Refactor Gate、Dependency Boundary Gate 与 Backend Regression。
4. 根据真实测试反馈继续修复 Runtime / Governance / 重复实现问题。
5. 执行 Workflow / Tool / Runtime 全量最终 Gate。
6. 全部重构领域最终 Gate 通过后，才能恢复 Phase 2.4 主线任务。

模块化目录、职责与迁移规则继续以 `docs/00-architecture/BACKEND_MODULE_ARCHITECTURE.md` 与 `docs/00-architecture/BACKEND_MODULE_MIGRATION_MAP.md` 为准。
