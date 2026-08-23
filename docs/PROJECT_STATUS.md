# 项目状态

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- 当前架构基线：远端 `main` 已进入 Backend 模块化整改实施阶段。
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- 当前：**Phase 2.4 Durable Scheduler Contract-first 实现中；Persistence Gate 尚未闭环。当前先完成模块化迁移残留修复、测试警告清理，再重新执行 Backend Regression 与 Scheduler Persistence Gate。**

## 本轮新增修复事实

基于远端 `main` 的开发准则继续处理上一轮模块化 Gate 与测试反馈：

1. `backend/scripts/test_ollama_embedding.py` 已从已删除的 `app.services.ollama_embedding_provider` 切换到唯一正式入口 `app.infrastructure.providers.ollama_embedding`。
2. Ollama 验证脚本补充中文模块职责、边界及关键外部依赖说明，不实现第二套 Provider。
3. `backend/pyproject.toml` 删除当前仓库声明的 `pytest-asyncio==0.25.0` 不支持的 `asyncio_default_test_loop_scope` 配置项，保留 session 级 fixture loop 配置，避免未知配置警告。
4. `docs/04-errors/ERR-0024-backend-module-refactor-test-boundary.md` 已记录本轮旧 Ollama Provider import 与 pytest 配置警告处理事实。

**以上为代码/文档修复事实，不代表开发者本地最新验证已经通过。**

## 当前待执行本地验证

先同步开发依赖，确保本地 `uv` 环境与仓库声明的开发依赖一致：

```powershell
cd backend
uv sync --dev
```

然后按固定顺序执行：

```powershell
uv run python -c "import pytest_asyncio; print(pytest_asyncio.__version__)"
uv run python -c "from app.main import app; print('APP_IMPORT_OK')"
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\01_scheduler_persistence_gate.ps1
```

若 Scheduler PostgreSQL Integration 仍出现 Windows Proactor / asyncpg `Event loop is closed`，只能依据最新失败栈修复测试生命周期；不得通过 JSON/JSONL 替代真实 PostgreSQL Persistence。

## Backend 模块化整改纪律

```text
远端 main 唯一基线
→ 领域职责唯一
→ 生产/测试/评估/验证 import 全量切换
→ 删除旧文件
→ 全仓旧路径搜索 = 0
→ 重复实现检查 = 0
→ 中文模块职责说明
→ targeted tests
→ Backend Regression
```

禁止兼容垫片、旧入口转发、双实现以及在 `app/services/` 复制 Provider。Provider 正式技术适配统一位于 `app/infrastructure/providers/`；数据库 Engine / Session 正式实现统一位于 `app/infrastructure/db/`。

## Phase 2.4 下一执行任务

1. 开发者本地重新执行 Backend Regression，确认本轮旧 Provider import 与 pytest 配置 warning 均已消失；
2. 执行模块化 Gate，确认旧 Provider import、旧领域文件、重复实现搜索为 0；
3. 执行 Scheduler Persistence Gate，确认 Migration、Repository targeted tests、真实 PostgreSQL integration 与 Backend Regression；
4. **只有 Persistence Gate 本地实际通过后**，继续 Scheduler API Contract；
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
