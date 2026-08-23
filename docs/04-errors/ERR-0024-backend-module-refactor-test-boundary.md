# ERR-0024 Backend 模块重构后的测试边界残留

## 1. 问题

开发者本地基于旧工作区执行 Backend Regression 与模块化 Gate 时出现：

- `tests/api_contract/test_runtime_http_rbac.py` 仍从已废弃的 `app.api.dependencies` 导入数据库依赖；
- `tests/api_real/test_scheduled_trigger_api.py` 与 `test_webhook_trigger_api.py` 仍从 `app.dependencies.db` 获取 `engine`；
- `scripts/evaluation/knowledge/run_governed_embedding_profile_smoke.py` 仍从 `app.dependencies.db` 获取 `SessionLocal`；
- unit 与 integration 层存在同名 `test_workflow_scheduler_repository.py`，pytest 以非包模式收集时产生 `import file mismatch`；
- 模块化 Gate 在开发者本地还发现多个 Embedding / Knowledge 验证脚本存在旧 Provider import 路径；
- 修复后完整 pytest 已消除业务测试中的两个 `AsyncMock` 未等待警告，并移除当前 `pytest-asyncio` 版本不支持的未知配置项；
- 上述旧 Provider 路径处理后，模块化 Gate 又发现 `scripts/test_ollama_embedding.py` 引用已删除的 `app.services.ollama_embedding_provider`；
- Ollama 路径处理后，模块化 Gate 继续发现 `scripts/dev/validate_pgvector.py` 引用已删除的 `app.services.vector_retrieval_provider`。

## 2. 根因

模块化重构已经将数据库 Session 与 Provider 技术适配分别收敛到 Infrastructure，但受影响测试、评估脚本和测试辅助脚本没有与生产代码同步完成全量迁移。

其中数据库正式边界为：

```text
API Handler
  -> app.dependencies.db.get_db
  -> app.infrastructure.db.session

Service / Runtime / Evaluation
  -> app.infrastructure.db.session.SessionLocal / engine
```

Provider 正式边界为：

```text
业务 / 评估 / 验证脚本
  -> app.infrastructure.providers
```

不得重新在 `app.services` 复制 Provider，也不得通过兼容垫片保留旧业务入口。

## 3. 已完成修复

本轮直接基于 `main` 完成：

1. Runtime HTTP Contract 测试切换到 `app.dependencies.db.get_db`；
2. Scheduled/Webhook Real API 测试直接使用 `app.infrastructure.db.session.engine`；
3. governed Embedding Profile smoke 直接使用 `app.infrastructure.db.session.SessionLocal`；
4. Scheduler Repository unit 测试改为唯一文件名 `test_workflow_scheduler_repository_unit.py`，删除旧同名 unit 文件；
5. 模块职责说明补充为中文，并明确测试/评估边界；
6. Embedding 验证脚本统一使用 `app.infrastructure.providers.embedding`，不保留第二套 Provider 实现；
7. Knowledge Retrieval 评估脚本统一使用 `app.infrastructure.db.session` 与 `app.infrastructure.providers`，不再引用已删除的旧 Provider 路径；
8. Scheduler Repository 单元测试把数据库执行结果从 `AsyncMock` 改为 `Mock`，避免把同步 Result API 模拟成 coroutine；
9. Ollama Embedding 验证脚本切换到唯一正式入口 `app.infrastructure.providers.ollama_embedding`，并补充中文模块职责、边界和外部依赖说明；
10. 移除仓库当前声明的 `pytest-asyncio==0.25.0` 不支持的 `asyncio_default_test_loop_scope` 配置项，保留会话级 fixture loop 配置，避免本地产生未知配置警告；
11. pgvector 验证脚本切换到唯一正式入口 `app.infrastructure.providers.vector_retrieval`，并补充中文模块职责、边界及关键外部依赖说明。

## 4. 当前实际验证结果

开发者本地在本轮修复前反馈为：

```text
APP_IMPORT_OK
378 passed, 2 skipped, 35 deselected
```

模块化 Gate 在该结果之后暴露的最后一个旧 Provider import 为：

```text
scripts/dev/validate_pgvector.py
-> app.services.vector_retrieval_provider
```

本轮已将该脚本切换到：

```text
app.infrastructure.providers.vector_retrieval
```

**以上最新代码修复尚未由开发者本地重新验证，因此不得记录模块化 Gate Passed 或 Backend Regression Passed。**

## 5. 预防

每个模块迁移单元必须同时检查：

```text
生产 import
测试 import
评估脚本 import
验证脚本 import
旧文件
旧路径搜索
重复实现
测试文件命名唯一性
模块职责说明
```

只有上述检查与实际 targeted tests / Backend Regression 全部完成后，才能将领域迁移标记为完成。
