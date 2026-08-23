# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main` 已进入 Backend 模块化整改实施阶段。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- 当前：**Phase 2.4 Durable Scheduler Contract-first 实现中；Persistence Gate 尚未闭环，当前优先修复模块化迁移后的测试/评估入口残留，再重新执行 Backend Regression 与 Scheduler Persistence Gate。**

## 本轮修复事实

基于远端 `main` 的开发准则执行了测试边界与重复模块清理：

1. Runtime HTTP Contract 测试改用唯一 FastAPI 数据库依赖 `app.dependencies.db.get_db`，不再引用不存在的 `app.api.dependencies`。
2. Scheduled/Webhook Real API 测试直接引用 `app.infrastructure.db.session.engine`；Application Service、Runtime、Evaluation 不通过 API Dependency 获取 Engine。
3. governed Embedding Profile smoke 直接引用 `app.infrastructure.db.session.SessionLocal`，不复制数据库 Session 实现。
4. Scheduler Repository unit 测试改为唯一文件名 `test_workflow_scheduler_repository_unit.py`，删除与 integration 层冲突的旧同名 unit 文件，避免 pytest module identity 冲突。
5. 受影响脚本/测试补充中文模块职责、边界和关键依赖说明。
6. Embedding Provider 验证脚本统一引用 `app.infrastructure.providers.embedding`，不保留旧 `services` Provider 路径或第二套实现。
7. 本轮测试边界问题记录为 `docs/04-errors/ERR-0024-backend-module-refactor-test-boundary.md`。

**以上均为代码/文档修复事实；开发者尚未在本地重新执行完整验证，因此不得记录为 Passed。**

## 当前必须执行的本地验证

```powershell
cd backend
uv run python -c "from app.main import app; print('APP_IMPORT_OK')"
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\01_scheduler_persistence_gate.ps1
```

若 Scheduler PostgreSQL Integration 仍出现 Windows Proactor / asyncpg `Event loop is closed`，只能依据最新失败栈修复测试生命周期；不得通过 JSON/JSONL 替代真实 PostgreSQL Persistence。

## Backend 模块化整改纪律

本次整改继续遵守：

```text
远端 main 唯一基线
→ 领域职责唯一
→ 生产/测试/评估 import 全量切换
→ 删除旧文件
→ 全仓旧路径搜索 = 0
→ 重复实现检查 = 0
→ 中文模块职责说明
→ targeted tests
→ Backend Regression
```

禁止兼容垫片、旧入口转发、双实现以及在 `app/services/` 复制 Provider。Provider 正式技术适配统一位于 `app/infrastructure/providers/`；数据库 Engine / Session 正式实现统一位于 `app/infrastructure/db/`。

## Phase 2.4 下一执行任务

1. 开发者本地重新执行 Backend Regression，确认本轮 5 个 collection error 已消失；
2. 执行模块化 Gate，确认旧 Provider import、旧领域文件、重复实现搜索为 0；
3. 执行 Scheduler Persistence Gate，确认 Migration、Repository targeted tests、真实 PostgreSQL integration 与 Backend Regression；
4. 若 Gate 通过，再继续 Scheduler API Contract；
5. 接入 Runtime persistence / lease / slot，补充 tenant isolation、misfire、Audit / Trace；
6. 完成 Tenant Safe Real API Gate 后再进入前端/API 联调。

## 开发纪律

- 远端 `main` 是唯一开发基线，不创建功能分支。
- 未实际执行的测试不得记录为 Passed。
- Runtime 数据必须使用真实 PostgreSQL；JSON/JSONL 仅用于版本化 evaluation dataset/result/baseline。
- Secret 不进入 Git、数据库明文、报告或 trace/audit。
- 代码、Phase、Acceptance、Error、Status 必须保持可追溯。
- 代码中的功能说明和注释统一使用中文。
- 每个新增或重构 Python 模块必须提供中文职责说明、边界及必要外部依赖。
- 同一业务功能只能保留一个正式实现；模块迁移完成后删除旧文件与旧路径。
- Provider 只能在 `app/infrastructure/providers/` 保留正式技术适配实现。
- Backend 模块化设计参照 `docs/00-architecture/BACKEND_MODULE_ARCHITECTURE.md`，具体迁移参照 `docs/00-architecture/BACKEND_MODULE_MIGRATION_MAP.md`。
