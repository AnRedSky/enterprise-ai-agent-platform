# Phase 1.4-E Provider Replacement Validation：执行检查点

> 更新时间：2026-08-19
>
> 本文记录当前阶段的离线 Mock Embedding 验证与真实 Provider 验收准备工作。按照 `docs/DEVELOPMENT.md`，未实际执行的测试或真实 Provider 联调不得标记为通过。

## 1. 当前任务状态

| ID | 任务 | 状态 | 责任角色 | 目标时间 |
|---|---|---|---|---|
| 1.4-E-01 | Mock Embedding + pgvector 5 条 Dataset 端到端向量入库/检索 | **代码已实现，待本地执行** | Backend / Knowledge | 2026-08-20 |
| 1.4-E-02 | 使用 Mock 结果生成 `vector_results.jsonl` 并执行 Quality Gate | **待本地执行** | Backend / QA | 2026-08-20 |
| 1.4-E-03 | lexical-v2 与 Mock Vector 指标比较 | **待 02** | Knowledge / QA | 2026-08-20 |
| 1.4-E-04 | 真实 Embedding Provider Replacement Validation | **待真实 Provider** | Backend / Knowledge | 2026-08-21 |
| 1.4-E-05 | 根据评测结果修复问题并补回归 | **待评测结果** | Backend | 2026-08-21 |
| 1.4-E-06 | Phase 1.4-E 最终验收 | **待 03/04/05** | Tech Lead | 2026-08-21 |

## 2. 本次工程变更

### 2.1 Deterministic Mock Embedding Provider

新增：

```text
backend/app/services/mock_embedding_provider.py
```

`MockEmbeddingProvider` 实现与现有 Embedding adapter 相同的 `embed(texts)` 异步接口，并具备：

- 固定输入产生固定向量。
- 使用 token 的 SHA-256 稳定映射到向量维度。
- 向量归一化，便于 cosine / pgvector 相似度计算。
- 支持中英文文本 token。
- 空文本直接拒绝。
- 维度由 `EMBEDDING_DIMENSION` 控制。

该实现是**离线检索测试 fixture**，不是语言模型，不代表真实 Embedding 的语义质量。

### 2.2 Vector Indexing 接入 Mock

`KnowledgeVectorIndexingService` 现在支持：

```text
EMBEDDING_PROVIDER=openai-compatible
EMBEDDING_PROVIDER=mock
```

当使用 `mock` 时：

```text
Knowledge Chunk
    ↓
MockEmbeddingProvider
    ↓
VectorRecord
    ↓
PgVectorRetrievalProvider
    ↓
PostgreSQL + pgvector
```

同时保留 embedding dimension 校验，防止测试数据绕过 pgvector contract。

### 2.3 配置

本地离线验证可使用：

```dotenv
EMBEDDING_PROVIDER=mock
EMBEDDING_MODEL=mock-semantic-v1
EMBEDDING_DIMENSION=1536
EMBEDDING_BATCH_SIZE=32

VECTOR_PROVIDER=pgvector
VECTOR_DB_URL=postgresql+asyncpg://agent:agent@localhost:5432/agent_platform
VECTOR_TOP_K=5
VECTOR_MIN_SCORE=0.0
```

真实 Provider 仍使用：

```dotenv
EMBEDDING_PROVIDER=openai-compatible
EMBEDDING_BASE_URL=<local-provider-endpoint>
EMBEDDING_API_KEY=<local-secret>
EMBEDDING_MODEL=<embedding-model>
```

所有真实 secret 只放未提交的 `backend/.env`。

## 3. 本地执行步骤

### Step 1：启动 PostgreSQL + pgvector

```powershell
docker compose up -d postgres redis
```

### Step 2：配置离线 Mock 模式

在 `backend/.env` 设置：

```dotenv
EMBEDDING_PROVIDER=mock
EMBEDDING_MODEL=mock-semantic-v1
EMBEDDING_DIMENSION=1536
VECTOR_PROVIDER=pgvector
VECTOR_DB_URL=postgresql+asyncpg://agent:agent@localhost:5432/agent_platform
```

不需要 API key，也不需要外部 Embedding 服务。

### Step 3：执行 Backend 测试

```powershell
cd backend
uv run pytest -q
```

### Step 4：执行 Mock Vector Retrieval Scenario

使用现有 Knowledge Registry / ingestion / vector-index API，在同一 Knowledge Base scope 下完成 5 条 Dataset query。每条结果必须记录：

- query
- mode=vector
- ranking / chunk ids
- latency_ms
- provider error（如有）

保存为本地：

```text
backend/evaluation/vector_results.jsonl
```

**该文件属于运行产物，不提交 Git。**

### Step 5：执行 Quality Gate

```powershell
uv run python scripts/evaluate_knowledge_retrieval_provider.py .\evaluation\vector_results.jsonl
```

门禁：

- Recall@K >= lexical-v2 baseline
- MRR >= lexical-v2 baseline
- provider error rate == 0
- Precision@K 作为观察指标
- latency 作为性能指标

## 4. Mock 验证边界

Mock 验证可以证明：

- Embedding contract 可以离线执行。
- batch embedding 行为稳定。
- embedding dimension contract 正常。
- Chunk → embedding → pgvector indexing 链路正常。
- pgvector upsert / search 链路正常。
- Knowledge Base scope / retrieval contract 可以联调。
- Evaluation runner 可以计算 Recall@K、Precision@K、MRR、latency、error rate。
- Provider 替换不会要求 Runtime 修改业务逻辑。

Mock 验证**不能**证明：

- 真实模型的语义理解质量。
- 真实模型跨语言 / 同义词 / 长文本语义表现。
- 真实 Embedding Provider 的网络、限流、鉴权、超时表现。
- 真实模型的最终 Recall@K / MRR 生产质量。

因此 Mock Quality Gate 通过后，Phase 1.4-E 仍不能标记“真实 Provider 验收完成”。

## 5. 测试记录

本次代码实现新增 Mock Provider 及对应 pytest；GitHub 开发环境没有执行用户本地 PostgreSQL/pgvector，因此运行结果必须由本地开发者执行后回填。

当前已有本地反馈：

- Backend pytest：此前全量通过。
- Frontend Vitest：此前通过。
- Frontend build：此前通过。
- Mock Embedding pytest：**待本地执行本次新增测试**。
- Mock + pgvector 端到端：**待本地执行**。
- Mock Quality Gate：**待生成本地 `vector_results.jsonl` 后执行**。
- Real Embedding Provider：**待真实资源可用后执行**。

## 6. 已知问题与解决方案

### 已知问题

1. 当前无法获得真实 Embedding 模型调用资源。
2. GitHub 开发环境无法代替用户本地 PostgreSQL/pgvector 环境。
3. Mock Embedding 是确定性 hash/token fixture，不是语言模型。
4. 当前没有后台索引队列，失败重建通过 API / 本地脚本触发。
5. 尚未实现跨 Version 的 `content_hash + embedding_model + embedding_dimension` embedding 复用。
6. Hybrid Retrieval 尚未进入实现。

### 解决方案

- 通过 `MockEmbeddingProvider` 先完成完全离线的 Vector Retrieval pipeline validation。
- Mock 与 OpenAI-compatible adapter 共用 embedding contract，替换时不修改 Knowledge Runtime。
- pgvector 仍然使用真实 PostgreSQL + pgvector，避免把 Vector DB 测试降级成纯内存测试。
- Quality Gate 缺少结果文件时保持 pending，不把 skip 当成通过。
- 真实 Provider secret 只放未提交 `backend/.env`。

## 7. 下一阶段任务清单

| 优先级 | 任务 | 责任角色 | 前置依赖 | 目标时间 |
|---|---|---|---|---|
| **P0** | 本地执行 Mock Embedding pytest + Backend 全量 pytest | Backend / QA | Mock Provider 代码 | 2026-08-20 |
| **P0** | PostgreSQL + pgvector 下完成 5 条 Dataset Mock Vector Retrieval | Backend / Knowledge | Docker pgvector | 2026-08-20 |
| **P0** | 生成 `vector_results.jsonl` 并运行 Mock Quality Gate | Backend / QA | Mock Vector Retrieval | 2026-08-20 |
| **P0** | 根据 Mock 结果修复 indexing / retrieval contract 问题 | Backend / Knowledge | Mock Quality Gate | 2026-08-21 |
| **P0** | 有真实 Embedding 资源后重新执行相同 Dataset 的真实 Provider 验收 | Backend / Knowledge / QA | Real Provider credentials | 待资源确认 |
| **P0** | 更新 Phase 1.4-E 最终验收与 `DEVELOPMENT.md` 状态 | Tech Lead | Mock/Real 评测结论 | 评测完成后 |
| **P1** | 设计 Hybrid Retrieval contract | Architecture / Backend | Phase 1.4-E 退出条件 | 2026-08-24 |
| **P1** | 实现 hybrid scoring / rerank + evaluation | Backend / QA | Hybrid contract | 2026-08-26 |
| **P1** | 实现 Hybrid Retrieval Debug UI | Frontend | Hybrid API contract | 2026-08-27 |

## 8. 变更追踪

本检查点关联近期变更：

- 项目状态与追溯规范：`e4e4d6e3e62a9fdd38627704347dee052ccb2f42`
- Provider validation suite：`0ca5f972`
- Mock Embedding Provider：`366b256b88e55c463521909ad7501a086f9a94c5`
- Mock Embedding tests：`26afc294a80dc84a1d7312e122aca4ae4ab9481f`
- Mock Vector indexing：`03842a4701563b6165403aa3869cb552fa088417`
- Mock configuration：`9b109cb348284ce2846d0807c7a656b3b2374a3c` / `316c801e62e030d8b0a260ab9927a288700d8aff`

## 9. 阶段退出条件

Phase 1.4-E 只有在以下条件全部满足后才能标记“完成”：

### Offline Mock validation

- [x] Mock Embedding Provider 已实现。
- [x] Mock 与 pgvector indexing 已接通。
- [x] Mock Provider 单元测试已加入。
- [ ] 本地 Mock + pgvector 端到端执行通过。
- [ ] Mock Quality Gate 通过。

### Real Provider validation

- [ ] 真实 Embedding Provider probe 通过。
- [ ] 5 条 Dataset 均完成真实 vector retrieval。
- [ ] `vector_results.jsonl` 已生成并经质量门禁验证。
- [ ] Recall@K / MRR 不低于 lexical-v2 baseline。
- [ ] provider error rate 为 0，或异常已有明确修复并重新验证。
- [ ] Backend pytest、Frontend npm test、Frontend npm run build 全部通过。
- [ ] 已知问题、解决方案、剩余风险全部记录。
- [ ] `DEVELOPMENT.md` 与阶段验收文档已同步更新。

在真实 Provider 条件未满足前，**不得将 Mock Quality Gate 结论写成真实 Provider 验收通过，也不得仅因 Mock 通过而进入 Hybrid Retrieval。**
