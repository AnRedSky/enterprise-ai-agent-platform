# Phase 2.4 Scheduler Persistence Gate：asyncpg 事件循环与旧 Provider import

## 1. 发生时间

2026-08-23

## 2. 现象

开发者本地执行 Scheduler Persistence Gate 时：

- Alembic upgrade/current 正常；
- Scheduler contract targeted tests：13 passed；
- Repository PostgreSQL integration 首个测试通过，第二个测试 `test_scheduler_repository_slot_claim_is_idempotent` 在 Windows ProactorEventLoop 下失败；
- asyncpg / SQLAlchemy 连接池复用已关闭事件循环，最终表现为 `RuntimeError: Event loop is closed` 与 `AttributeError: 'NoneType' object has no attribute 'send'`；
- Backend 全量 pytest 同时出现 unit/integration 同名测试模块的 `import file mismatch`；
- Backend module-refactor Gate 发现 `scripts/evaluation/embedding/validate_embedding_provider.py` 仍从已迁移的 `app.services.embedding_provider` 导入 Provider。

## 3. 根因

### 3.1 asyncpg 生命周期边界

当前 `app.infrastructure.db` 是唯一正式 Engine / Session 入口，但 pytest 只将 async fixture loop 设置为 session scope，async test 默认仍可能使用 function scope event loop。SQLAlchemy asyncpg pool 中的连接可能因此在后续测试中绑定到已经关闭的 ProactorEventLoop。

### 3.2 pytest 同名模块收集

`tests/unit/` 与 `tests/integration/` 存在同名测试文件。pytest 默认 import mode 会将测试模块以顶层模块名导入，导致同名模块之间发生 `import file mismatch`。

### 3.3 Provider 迁移后的旧 import

Embedding Provider 正式实现已经集中在 `app.infrastructure.providers.embedding`。验证脚本仍引用旧 `app.services.embedding_provider`，虽然生产旧文件已经删除，但脚本 import 未完成迁移，因此被模块化 Gate 正确拦截。

## 4. 修复

本次修复保持业务行为不变：

1. pytest `asyncio_default_fixture_loop_scope` 保持 `session`；
2. 新增 `asyncio_default_test_loop_scope = "session"`，使 async test 与 async fixture 使用同一 session loop；
3. 新增 pytest `--import-mode=importlib`，允许 unit/integration 保持同名测试文件而不发生模块名冲突；
4. Embedding 验证脚本改用 canonical `app.infrastructure.providers.embedding`；
5. 为验证脚本补充中文模块职责、边界及唯一 Provider 入口说明。

## 5. 验收纪律

本环境不能访问开发者 Windows 本地 PostgreSQL/Ollama 环境，因此本记录不声明本地 Gate 已通过。必须由开发者在本地重新执行：

```powershell
cd backend
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\integration\01_scheduler_persistence_gate.ps1
```

只有上述实际结果通过后，Phase 2.4 Persistence Gate 才能继续进入 Scheduler API Contract 与 Runtime persistence / lease / slot 闭环。
