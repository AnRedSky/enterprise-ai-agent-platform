# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main` 已进入 Backend 模块化整改实施阶段。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- 当前：**Phase 2.4 Durable Scheduler Contract-first + Persistence 第一版已完成；同时继续执行 Backend 模块化整改，主线任务暂停，直到既有重构任务全部完成。**

## 最新 main 基线

本轮开始前远端 `main` 最新提交为 `62b280c`，其后已合入 Scheduler 时间类型归一化相关修复。本轮直接基于最新 `main` 继续开发，并保持所有变更直接提交 `main`，不创建分支。

开发准则明确要求：模块重构必须完成生产/测试 import 全量切换、旧文件删除、旧路径搜索为 0、重复实现检查、中文模块说明、targeted tests 与 Backend Regression 后才能标记完成；同时禁止兼容垫片和第二套 Provider。

## 本轮实际代码变更

1. 完成 Memory Service 从 `app/services/memory_service.py` 到 `app/services/memory/` 的物理迁移。
2. 完成 Memory Runtime 上下文从 `app/runtime/memory_context.py` 到 `app/runtime/memory/` 的物理迁移。
3. 删除两个旧模块路径，不保留转发文件或兼容实现。
4. Memory 测试 import 全量切换到正式模块入口，并补充测试模块职责说明。
5. Module Refactor Gate 增加 Memory 目录、旧路径、重复根文件和 targeted tests 检查。
6. 新增/重构 Python 模块补充中文职责、边界和关键外部依赖说明。
7. 未新增数据库 Migration；Memory 现有 PostgreSQL 数据结构不因目录重构发生变化。

## 当前模块重构完成度

已完成：

- Agent
- Knowledge + Provider
- Memory（本轮）

仍未完成：

- Model
- Workflow
- Trigger
- Organization
- Governance
- Observability
- Tool
- API `v1/<domain>` 收敛
- Runtime 其他领域目录收敛

因此，**本轮不得转入新的业务主线开发**。后续继续按 Migration Map 逐领域完成物理迁移，直到全部重构单元满足验收条件。

## 本地验证原则

本轮代码提交由远端仓库直接完成，当前对新增 Memory 迁移代码没有声称已在开发者本地执行通过。根据开发准则，测试结果只能记录实际本地执行结果，GitHub Actions 不作为开发测试或验收依据。

### 本轮建议本地验证顺序

```powershell
cd backend
uv sync --dev
uv run python -c "from app.main import app; print('APP_IMPORT_OK')"
uv run pytest -q tests/unit/test_memory_service.py tests/unit/test_memory_context.py
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1
uv run pytest -q
```

如果本地 Gate 发现旧 import、重复实现或回归，必须基于真实失败继续修复，不得通过兼容垫片绕过 Gate。

## 下一执行任务：继续模块化整改

优先顺序保持：

1. Model 领域物理迁移：Service / Contract / Governance / Runtime / Provider 边界一次性收敛；
2. Workflow 领域物理迁移：Registry / Execution / Governance 与 Runtime 分离；
3. Trigger 领域物理迁移：Scheduled / Webhook 统一进入 Trigger 子模块；
4. Organization / Governance / Observability 按实际职责完成领域收敛；
5. Tool Service 与 `app/tools/` 技术实现完成唯一 Runtime 边界；
6. API 收敛到 `app/api/v1/<domain>/`，保持现有 HTTP Contract 不变；
7. 全部重构领域逐一通过 Module Refactor Gate 后，才恢复 Phase 2.4 主线后续任务。

模块化目录、职责与迁移规则继续以 `docs/00-architecture/BACKEND_MODULE_ARCHITECTURE.md` 与 `docs/00-architecture/BACKEND_MODULE_MIGRATION_MAP.md` 为准。
