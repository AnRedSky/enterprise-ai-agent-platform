# ERR-0024 Backend 模块重构后的测试边界残留

## 1. 问题

开发者本地基于旧工作区执行 Backend Regression 时出现：

- `tests/api_contract/test_runtime_http_rbac.py` 仍从已废弃的 `app.api.dependencies` 导入数据库依赖；
- `tests/api_real/test_scheduled_trigger_api.py` 与 `test_webhook_trigger_api.py` 仍从 `app.dependencies.db` 获取 `engine`；
- `scripts/evaluation/knowledge/run_governed_embedding_profile_smoke.py` 仍从 `app.dependencies.db` 获取 `SessionLocal`；
- unit 与 integration 层存在同名 `test_workflow_scheduler_repository.py`，pytest 以非包模式收集时产生 `import file mismatch`；
- 模块化 Gate 在开发者本地还发现 Embedding 验证脚本存在旧 Provider import 路径。

## 2. 根因

模块化重构已经将数据库 Session 与 Provider 技术适配分别收敛到 Infrastructure，但受影响测试、评估脚本和测试文件命名没有与生产代码同步完成全量迁移。

其中数据库正式边界为：

```text
API Handler
  -> app.dependencies.db.get_db
  -> app.infrastructure.db.session

Service / Runtime / Evaluation
  -> app.infrastructure.db.session.SessionLocal / engine
```

不得重新在 `app.api` 或 `app.dependencies.db` 中复制 Engine / SessionLocal，也不得通过兼容垫片保留旧业务入口。

## 3. 修复

本次直接基于 `main` 完成：

1. Runtime HTTP Contract 测试切换到 `app.dependencies.db.get_db`；
2. Scheduled/Webhook Real API 测试直接使用 `app.infrastructure.db.session.engine`；
3. governed Embedding Profile smoke 直接使用 `app.infrastructure.db.session.SessionLocal`；
4. Scheduler Repository unit 测试改为唯一文件名 `test_workflow_scheduler_repository_unit.py`，删除旧同名 unit 文件；
5. 模块职责说明补充为中文，并明确测试/评估边界；
6. Embedding 验证脚本统一使用 `app.infrastructure.providers.embedding`，不保留第二套 Provider 实现。

## 4. 验证边界

以上为代码修复事实，不代表开发者本地测试已经通过。

本地重新验证必须至少执行：

```powershell
cd backend
uv run python -c "from app.main import app; print('APP_IMPORT_OK')"
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\module-refactor\01_backend_module_refactor_gate.ps1
```

涉及 Scheduler PostgreSQL 持久化时继续执行对应 Integration Gate，并确认 PostgreSQL asyncpg 生命周期不存在跨事件循环复用问题。

## 5. 预防

每个模块迁移单元必须同时检查：

```text
生产 import
测试 import
评估脚本 import
旧文件
旧路径搜索
重复实现
测试文件命名唯一性
模块职责说明
```

只有上述检查与实际 targeted tests / Backend Regression 全部完成后，才能将领域迁移标记为完成。
