# Phase 1.4-E Mock Embedding 实现记录

> 日期：2026-08-19
> 状态：代码实现完成，等待用户本地执行验证

## 1. 任务目的

由于当前无法获得真实 Embedding 模型调用资源，本阶段先建立完全离线、确定性的 Mock Embedding 路径，用于验证：

`Chunk → Embedding → pgvector → Vector Retrieval → Evaluation`

该验证用于证明工程链路，不用于证明真实 Embedding 模型的语义质量。

## 2. 实现范围

### 2.1 `MockEmbeddingProvider`

文件：

```text
backend/app/services/mock_embedding_provider.py
```

实现：

- 与现有 Embedding adapter 使用相同的异步 `embed(texts)` 接口。
- SHA-256 token 映射保证相同输入得到相同向量。
- 支持英文、数字和中文 token。
- 向量归一化，便于 cosine similarity / pgvector 计算。
- 支持配置化 dimension。
- 空输入/空白文本返回明确 provider error。

设计限制：这是 deterministic token-hashing fixture，不是 Transformer/LLM embedding 模型。

### 2.2 Knowledge Vector Indexing

文件：

```text
backend/app/services/knowledge_vector_indexing.py
```

支持：

```text
EMBEDDING_PROVIDER=openai-compatible
EMBEDDING_PROVIDER=mock
```

Mock 模式仍然使用真实 `PgVectorRetrievalProvider`，因此不会把 Vector DB 测试降级为纯内存测试。

新增 embedding dimension 检查：任何 embedding 长度与 `EMBEDDING_DIMENSION` 不一致都会失败并将 Version 标记为 failed。

### 2.3 配置

`backend/app/core/config.py` 增加 Mock 模式设计说明。

`backend/.env.example` 增加：

```dotenv
# `mock` is deterministic and offline; use it for local vector pipeline validation.
EMBEDDING_PROVIDER=none
EMBEDDING_MODEL=
EMBEDDING_DIMENSION=1536
EMBEDDING_BATCH_SIZE=32
```

本地 Mock 验证建议：

```dotenv
EMBEDDING_PROVIDER=mock
EMBEDDING_MODEL=mock-semantic-v1
EMBEDDING_DIMENSION=1536
VECTOR_PROVIDER=pgvector
VECTOR_DB_URL=postgresql+asyncpg://agent:agent@localhost:5432/agent_platform
```

## 3. 测试

新增：

```text
backend/tests/test_mock_embedding_provider.py
```

覆盖：

1. 同一输入产生完全相同的向量。
2. 向量维度正确并完成归一化。
3. 共享 token 的文本相似度高于无关文本。
4. 空白文本被拒绝。

本次代码提交没有执行用户本地 pytest，因此测试状态必须由本地开发者实际执行后回填。

## 4. 本地验收

### 4.1 Backend regression

```powershell
cd backend
uv run pytest -q
```

### 4.2 Mock + pgvector

启动：

```powershell
docker compose up -d postgres redis
```

`.env`：

```dotenv
EMBEDDING_PROVIDER=mock
EMBEDDING_MODEL=mock-semantic-v1
EMBEDDING_DIMENSION=1536
VECTOR_PROVIDER=pgvector
VECTOR_DB_URL=postgresql+asyncpg://agent:agent@localhost:5432/agent_platform
VECTOR_TOP_K=5
VECTOR_MIN_SCORE=0.0
```

然后执行现有 Phase 1.4-E provider validation suite，并使用固定的 5 条 Dataset 完成向量索引和检索。

### 4.3 Evaluation

结果写入本地：

```text
backend/evaluation/vector_results.jsonl
```

再执行：

```powershell
uv run python scripts/evaluate_knowledge_retrieval_provider.py .\evaluation\vector_results.jsonl
```

不能手工编造 `vector_results.jsonl`；必须由实际检索产生。

## 5. 验收标准

Mock 验证至少确认：

- embedding contract 正常。
- embedding dimension contract 正常。
- pgvector upsert/search 正常。
- Knowledge Base scope 正常。
- Vector retrieval ranking 正常。
- Evaluation runner 正常。
- provider error rate 统计正常。

如果 Mock Quality Gate 通过，只能得出“离线 Vector Retrieval pipeline 可用”的结论。

不能得出：

- 真实模型语义质量已通过。
- 真实 Provider 网络/鉴权/限流已通过。
- 生产 Recall@K / MRR 已通过。

## 6. 已知问题

- 真实 Embedding Provider 当前不可用，真实验收保持 pending。
- Mock provider 不具备真实模型语义泛化能力。
- 跨 Version embedding 复用尚未实现。
- Hybrid Retrieval 尚未开始。

## 7. 下一阶段任务

| 优先级 | 任务 | 责任角色 | 状态 |
|---|---|---|---|
| P0 | 本地执行 Mock Embedding pytest | Backend / QA | 待执行 |
| P0 | 本地执行 Mock + pgvector 端到端 | Backend / Knowledge | 待执行 |
| P0 | 生成真实运行产物 `vector_results.jsonl` | Backend / QA | 待执行 |
| P0 | 执行 Mock Quality Gate 并记录指标 | QA / Knowledge | 待执行 |
| P0 | 有真实资源后使用相同 Dataset 重跑 Real Embedding | Backend / Knowledge | 待资源 |
| P1 | Phase 1.4-E 最终验收 | Tech Lead | 待 P0 |
| P1 | Hybrid Retrieval contract | Architecture / Backend | 待 Phase 1.4-E |

## 8. 变更追踪

- Mock Provider：`366b256b88e55c463521909ad7501a086f9a94c5`
- Mock Provider tests：`26afc294a80dc84a1d7312e122aca4ae4ab9481f`
- Vector indexing integration：`03842a4701563b6165403aa3869cb552fa088417`
- Config：`9b109cb348284ce2846d0807c7a656b3b2374a3c`
- `.env.example`：`316c801e62e030d8b0a260ab9927a288700d8aff`
- Checkpoint：`792aa3c255e4cce8b9f4a8d1cf0e2e9d7a803aa6`
