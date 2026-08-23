# ERR-0024 Backend 模块重构后的测试边界残留

## 1. 问题

开发者本地基于旧工作区执行 Backend Regression 时出现：

- `tests/api_contract/test_runtime_http_rbac.py` 仍从已废弃的 `app.api.dependencies` 导入数据库依赖；
- `tests/api_real/test_scheduled_trigger_api.py` 与 `test_webhook_trigger_api.py` 仍从 `app.dependencies.db` 获取 `engine`；
- `scripts/evaluation/knowledge/run_governed_embedding_profile_smoke.py` 仍从 `app.dependencies.db` 获取 `SessionLocal`；
- unit 与 integration 层存在同名 `test_workflow_scheduler_repository.py`，pytest 以非包模式收集时产生 `import file mismatch`；
- 模块化 Gate 在开发者本地还发现 Embedding 验证脚本存在旧 Provider import 路径；
- 修复后完整 pytest 已消除业务测试中的两个 `AsyncMock` 未等待警告，但本地仍报告 `asyncio_default_test_loop_scope` 配置项未知，说明当前本地 pytest-asyncio 实际版本与仓库声明的开发依赖未同步。

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

本轮直接基于 `main` 完成：

1. Runtime HTTP Contract 测试切换到 `app.dependencies.db.get_db`；
2. Scheduled/Webhook Real API 测试直接使用 `app.infrastructure.db.session.engine`；
3. governed Embedding Profile smoke 直接使用 `app.infrastructure.db.session.SessionLocal`；
4. Scheduler Repository unit 测试改为唯一文件名 `test_workflow_scheduler_repository_unit.py`，删除旧同名 unit 文件；
5. 模块职责说明补充为中文，并明确测试/评估边界；
6. Embedding 验证脚本统一使用 `app.infrastructure.providers.embedding`，不保留第二套 Provider 实现；
7. Knowledge Retrieval 评估脚本统一使用 `app.infrastructure.db.session` 与 `app.infrastructure.providers`，不再引用已删除的旧 Provider 路径；
8. Scheduler Repository 单元测试把数据库执行结果从 `AsyncMock` 改为 `Mock`，避免把同步 Result API 模拟成 coroutine，从根源消除 `coroutine ... was never awaited` 警告。

## 4. 当前实际验证结果

开发者本地最新反馈为：

```text
APP_IMPORT_OK
378 passed, 2 skipped, 35 deselected, 3 warnings
```

模块化 Gate 随后暴露了新的旧 Provider import：

```text
scripts/evaluation/knowledge/run_knowledge_retrieval_evaluation.py
-> app.services.mock_embedding_provider
```

该旧路径已在本轮修复为唯一正式 Provider 入口：

```text
app.infrastructure.providers.MockEmbeddingProvider
app.infrastructure.providers.PgVectorRetrievalProvider
app.infrastructure.providers.VectorRecord
```

因此，在重新执行 Gate 前不得记录模块化 Gate Passed。

另外，pytest 的 `asyncio_default_test_loop_scope` 未知配置警告不能通过删除配置掩盖，因为该配置用于防止 SQLAlchemy asyncpg 连接池跨事件循环复用。应先让本地环境通过 `uv sync` 与仓库声明的 `pytest-asyncio==0.25.0` 对齐，再重新验证。

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