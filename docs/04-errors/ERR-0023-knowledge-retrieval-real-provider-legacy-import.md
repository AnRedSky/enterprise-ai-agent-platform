# ERR-0023：Knowledge Retrieval Real Provider 评估脚本保留旧 Provider 导入路径

## 1. 问题现象

开发者在 `main` 最新基线执行 Backend 模块化整改 Gate 时，Gate 在旧路径搜索阶段发现：

```text
scripts/evaluation/knowledge/run_knowledge_retrieval_real_provider.py
from app.services.vector_knowledge_retrieval import VectorKnowledgeRetrievalService
```

此前本地模块化 Gate 已经针对 Knowledge / Provider 领域完成生产代码与测试导入迁移，但评估脚本仍引用已删除的 `app.services` Provider 路径，因此 Gate 不能完成“全仓旧路径搜索 = 0”。

## 2. 根因

Knowledge Retrieval 与 Embedding / Vector Provider 已完成正式模块化迁移：

- Knowledge 领域实现统一位于 `app.services.knowledge`；
- 外部技术 Provider 统一位于 `app.infrastructure.providers`；
- 旧 Provider 文件不得恢复，也不得通过兼容垫片继续暴露。

评估脚本属于 `scripts/evaluation`，不在 Backend 默认业务 Service 目录中，前序迁移只修复了生产代码和受影响测试，遗漏了真实 Provider 评估脚本中的旧 import。

## 3. 修复

将评估脚本的依赖统一收敛到正式模块入口：

- `EmbeddingProviderError`、`OllamaEmbeddingProvider`、`OpenAICompatibleEmbeddingProvider`、`PgVectorRetrievalProvider`、`VectorRecord` → `app.infrastructure.providers`；
- `VectorKnowledgeRetrievalService` → `app.services.knowledge.vector_retrieval`。

不新增兼容入口、不复制 Provider 实现，不改变评估运行逻辑。

## 4. 预防

模块化迁移 Gate 必须覆盖：

1. 生产代码 import；
2. 测试 import；
3. evaluation / dev 脚本 import；
4. 旧文件与旧目录删除；
5. 全仓旧路径搜索；
6. 重复实现检查；
7. 领域 targeted tests 与 Backend Regression。

## 5. 验证边界

代码修复已提交到 `main`；本记录不把尚未由开发者重新执行的模块化 Gate 或 Backend Regression 标记为通过。

开发者下一步应重新执行模块化 Gate；通过后继续执行 Scheduler Persistence Gate。Scheduler Persistence Gate 当前用户反馈中的首个 PostgreSQL FK 失败对应测试 fixture 已在最新 `main` 中补齐 `WorkflowTrigger`，因此应以修复后的最新 `main` 实际结果继续判断，不能把旧失败结果直接作为当前状态。
