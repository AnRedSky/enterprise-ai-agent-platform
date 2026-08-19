# Phase 1.4-E Mock Embedding 实现记录

> 日期：2026-08-19
> 状态：Mock Embedding、分层环境配置、PostgreSQL + pgvector round-trip、自动 Retrieval Evaluation Runner 已实现；等待本地完整 Phase 1.4-E Quality Gate 回归

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

### 2.3 分层环境配置

文件：

```text
backend/app/core/config.py
backend/.env.example
backend/tests/test_config_environment.py
```

配置加载顺序（低 → 高）：

```text
.env.example
  ↓
.env
  ↓
.env.local
  ↓
.env.${APP_ENV}
  ↓
.env.${APP_ENV}.local
  ↓
ENV_FILE 指定文件
  ↓
进程环境变量（最高优先级）
```

说明：

- 默认 `APP_ENV=development`，因此默认选择 `.env.development` / `.env.development.local`。
- 如果没有任何本地 `.env` 文件，`.env.example` 作为最低优先级 fallback，保证 fresh checkout 可以直接启动。
- 测试环境建议在启动命令中设置 `APP_ENV=test`，从而加载 `.env.test` / `.env.test.local`。
- staging / production 使用对应 `APP_ENV`，或通过 `ENV_FILE` 指定部署环境文件。
- `.env.example` 只提供安全默认模板，不包含任何真实密钥。
- `ENV_FILE` 支持容器、部署脚本等无法依赖固定文件名的场景。
- 绝对 `ENV_FILE` 路径保持原样，不会被当前操作系统重新拼接。例如 Windows 测试环境中的 `/run/secrets/agent.env` 必须仍保持该 Unix 容器路径；相对 `ENV_FILE` 则相对于 backend 根目录解析。
- 进程环境变量始终覆盖所有文件中的同名配置，便于 CI、容器和部署平台注入配置。

### 2.4 自动 Retrieval Evaluation Runner

新增：

```text
backend/scripts/run_knowledge_retrieval_evaluation.py
backend/evaluation/knowledge_retrieval_fixture.jsonl
```

Runner 在测试数据库中创建临时 Knowledge Base / Document / Version / Chunk Fixture，使用当前 `MockEmbeddingProvider` 生成 embedding，再通过真实 `PgVectorRetrievalProvider` 完成 upsert 和 scoped search，最终生成：

```text
backend/evaluation/vector_results.jsonl
```

Fixture 使用稳定 UUID 映射保存到 PostgreSQL，结果文件恢复为 Evaluation Dataset 使用的逻辑 `chunk_id`，因此不会修改固定 Dataset 的相关性标注。

Runner 在完成结果生成后自动清理临时 Knowledge Base 数据，不把测试数据残留到开发数据库。

设计约束：

- 不直接构造 ranking 结果。
- ranking 必须来自真实 pgvector search。
- provider 异常写入 `error` 字段，并由 Quality Gate 统计。
- 仅允许 `EMBEDDING_PROVIDER=mock` + `VECTOR_PROVIDER=pgvector` 的离线验证模式。
- 不使用真实模型语义质量作为 Mock Quality Gate 的结论。

### 2.5 一键 Phase 1.4-E Quality Gate

`backend/scripts/run_phase_1_4_e_provider_validation.ps1` 第 4 阶段现在自动执行：

```text
run_knowledge_retrieval_evaluation.py
        ↓
vector_results.jsonl
        ↓
evaluate_knowledge_retrieval_provider.py
        ↓
Recall@3 / Precision@3 / MRR / latency / error rate
        ↓
Quality Gate
```

因此不再依赖人工准备 `vector_results.jsonl`。

## 3. 测试

新增：

```text
backend/tests/test_mock_embedding_provider.py
backend/tests/test_config_environment.py
```

覆盖：

1. 同一输入产生完全相同的向量。
2. 向量维度正确并完成归一化。
3. 共享 token 的文本相似度高于无关文本。
4. 空白文本被拒绝。
5. 默认 development 环境文件选择。
6. `APP_ENV=test` 能选择测试环境文件。
7. `ENV_FILE` 位于文件层级最高位置。
8. Unix 风格绝对 `ENV_FILE` 路径在 Windows 上保持原样。
9. fresh checkout 存在 `.env.example`。

### 3.1 本地测试反馈与修复

2026-08-19 本地 Windows 环境曾执行：

```text
138 passed, 1 failed
```

唯一失败项：`test_explicit_env_file_has_highest_file_precedence`。原因是旧实现直接执行 `BACKEND_ROOT / explicit`，导致 Windows 将 Unix 容器路径 `/run/secrets/agent.env` 转换成 `D:\run\secrets\agent.env`。

已修复为：

- 绝对 `ENV_FILE`：原样保留。
- 相对 `ENV_FILE`：解析为 `BACKEND_ROOT / ENV_FILE`。

修复提交：`db977af7e1a73068eae63bd44d03640091f44a6a`。

用户随后本地反馈 pgvector round-trip：

```text
pgvector validation passed: dimension=1536, top_k=5, score=1.0
```

该结果确认 PostgreSQL + pgvector upsert/search 基础链路已通过。

本次新增 Evaluation Runner / Phase Gate 修改通过 GitHub 提交完成，但未在本消息环境中执行用户本地数据库测试；最终测试状态必须由本地开发者回归后记录。

## 4. 本地验收

### 4.1 Fresh checkout 环境配置检查

在没有 `.env` / `.env.local` / `.env.development*` 的情况下：

```powershell
cd backend
$env:APP_ENV = "development"
uv run python -c "from app.core.config import settings; print('env=', settings.app_env); print('embedding=', settings.embedding_provider); print('vector=', settings.vector_provider); print('dimension=', settings.embedding_dimension)"
```

预期：

```text
env= development
embedding= mock
vector= pgvector
dimension= 1536
```

不要打印任何 API Key 或密码。

### 4.2 Backend regression

```powershell
uv run pytest -q
```

### 4.3 Mock + pgvector Round-trip

启动：

```powershell
docker compose up -d postgres redis
```

然后：

```powershell
uv run python scripts/validate_pgvector.py
```

当前本地已验证：

```text
pgvector validation passed: dimension=1536, top_k=5, score=1.0
```

### 4.4 完整 Retrieval Evaluation

执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_phase_1_4_e_provider_validation.ps1
```

或者仅执行 Retrieval Evaluation：

```powershell
uv run python scripts/run_knowledge_retrieval_evaluation.py --k 3
uv run python scripts/evaluate_knowledge_retrieval_provider.py .\evaluation\vector_results.jsonl --k 3
```

结果写入：

```text
backend/evaluation/vector_results.jsonl
```

不能手工编造 `vector_results.jsonl`；必须由实际 Mock Embedding + PostgreSQL/pgvector 检索产生。

## 5. 验收标准

Mock 验证至少确认：

- embedding contract 正常。
- embedding dimension contract 正常。
- pgvector upsert/search 正常。
- Knowledge Base scope 正常。
- Vector retrieval ranking 来自实际 pgvector 查询。
- Evaluation Runner 正常生成 JSONL。
- provider error rate 统计正常。
- Recall@3、MRR 不低于 baseline。
- error rate 必须为 0。
- 环境文件在 development / test / staging / production 场景下可以通过 `APP_ENV` 或 `ENV_FILE` 选择，且进程环境变量具有最高优先级。
- fresh checkout 在没有任何 `.env` 文件时可以通过 `.env.example` 启动。
- Windows / Linux / container 场景下绝对 `ENV_FILE` 路径语义保持一致。

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
- 当前 Evaluation Runner 依赖测试数据库至少存在一个用户，用于满足 Knowledge Base / Document Version 外键约束。

## 7. 当前任务状态与下一阶段任务

| 优先级 | 任务 | 责任角色 | 状态 | 目标时间 |
|---|---|---|---|---|
| P0 | 分层环境配置与 `.env.example` 补充 | Backend / DevOps | 已实现 | 2026-08-19 |
| P0 | Windows / container `ENV_FILE` 路径兼容 | Backend / DevOps | 已修复 | 2026-08-19 |
| P0 | Mock Embedding 单元测试 | Backend / QA | 已实现 | 2026-08-19 |
| P0 | PostgreSQL + pgvector round-trip | Backend / Knowledge | 已本地通过 | 2026-08-19 |
| P0 | 自动生成 `vector_results.jsonl` | Backend / QA | 已实现，待本地执行 | 2026-08-20 |
| P0 | Mock Retrieval Quality Gate | QA / Knowledge | 已接入一键脚本，待本地执行 | 2026-08-20 |
| P0 | 完整 Phase 1.4-E 回归验收 | Tech Lead | 待 P0 本地回归 | 2026-08-20 |
| P0 | 有真实资源后使用相同 Dataset 重跑 Real Embedding | Backend / Knowledge | 待资源 | 待定 |
| P1 | Retrieval failure / fallback 策略完善 | Backend / Architecture | 待 Phase 1.4-E | 2026-08-21 |
| P1 | Incremental / rebuild indexing 策略 | Backend / Knowledge | 待 Phase 1.4-E | 2026-08-24 |
| P1 | Hybrid Retrieval contract | Architecture / Backend | 待 Phase 1.4-E | 2026-08-24 |

## 8. 变更追踪

- Mock Provider：`366b256b88e55c463521909ad7501a086f9a94c5`
- Mock Provider tests：`26afc294a80dc84a1d7312e122aca4ae4ab9481f`
- Vector indexing integration：`03842a4701563b6165403aa3869cb552fa088417`
- Layered environment config：`c6977460235425469db9dbc36fac4369cbb28d66`
- `.env.example`：`1665506c39069c340a70c9193ca962cc6b293000`
- Environment selection tests：`6d57d866091a55c489e43376d434fad60c1fe7f8`
- `.env.example` fallback：`0e188a8e545288f84f2364d0c1b62dab68d62267`
- Environment precedence tests：`2278b7483f8f085f9a88ecb21af8ff09f12c4231`
- Mock validation environment support：`ad23e400`
- Windows / container explicit `ENV_FILE` compatibility fix：`db977af7e1a73068eae63bd44d03640091f44a6a`
- pgvector nullable scope parameter fix：`ffe9d62e5d515eda1b4ce61bbe4e907b2cf49de0`
- Retrieval fixture：`546a2d452acf98c81640bc078e204489f7b049e7`
- Retrieval Evaluation Runner：`d19007cba18c065bc5a8b64b96d4f4b4efd90cdb`
- Phase Quality Gate integration：`40c8c0838cf6f1e7935ad9dd63a164508b8304d7`
