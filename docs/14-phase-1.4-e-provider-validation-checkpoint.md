# Phase 1.4-E Provider Replacement Validation：执行检查点

> 更新时间：2026-08-19
>
> 本文记录当前阶段在 GitHub `main` 上已经完成的工程准备工作，以及必须由本地开发环境产生的真实 Provider 验收证据。按照 `docs/DEVELOPMENT.md`，未实际执行的测试或 Provider 联调不得标记为通过。

## 1. 当前任务状态

| ID | 任务 | 状态 | 责任角色 | 目标时间 |
|---|---|---|---|---|
| 1.4-E-01 | 真实 Embedding Provider + 5 条 Dataset 端到端向量入库/检索 | **待本地执行** | Backend / Knowledge | 2026-08-20 |
| 1.4-E-02 | 采集 `vector_results.jsonl` 并执行 Quality Gate | **待 01** | Backend / QA | 2026-08-20 |
| 1.4-E-03 | lexical-v2 与 vector 指标比较 | **待 02** | Knowledge / QA | 2026-08-20 |
| 1.4-E-04 | 根据真实结果修复问题并补回归 | **待评测结果** | Backend | 2026-08-21 |
| 1.4-E-05 | Phase 1.4-E 最终验收 | **待 03/04** | Tech Lead | 2026-08-21 |

## 2. 本次工程变更

### 2.1 Provider validation suite

新增：

```text
backend/scripts/run_phase_1_4_e_provider_validation.ps1
```

该脚本统一串联：

1. Embedding provider contract test + real provider probe。
2. PostgreSQL/pgvector contract test + round-trip probe。
3. Backend 全量 pytest。
4. 若存在 `backend/evaluation/vector_results.jsonl`，自动执行 Retrieval Provider Quality Gate。
5. 若结果文件不存在，只报告“待评测”，不会伪造通过。

### 2.2 已有真实 Provider probe

当前仓库已有：

- `backend/scripts/run_embedding_provider_validation.ps1`
- `backend/scripts/validate_embedding_provider.py`
- `backend/scripts/run_pgvector_validation.ps1`
- `backend/scripts/validate_pgvector.py`
- `backend/scripts/evaluate_knowledge_retrieval_provider.py`

Embedding probe 要求 `EMBEDDING_PROVIDER=openai-compatible` 以及本地 `.env` 中的 endpoint、API key、model；pgvector probe 要求 `VECTOR_PROVIDER=pgvector` 与 `VECTOR_DB_URL`。这些 probe 只验证真实环境，不提交任何密钥或运行结果。

### 2.3 配置能力

当前 Embedding 配置已经支持：

```text
EMBEDDING_PROVIDER
EMBEDDING_BASE_URL
EMBEDDING_API_KEY
EMBEDDING_MODEL
EMBEDDING_TIMEOUT_SECONDS
EMBEDDING_DIMENSION
EMBEDDING_BATCH_SIZE=32
```

Vector 配置保持：

```text
VECTOR_PROVIDER
VECTOR_DB_URL
VECTOR_DB_COLLECTION
VECTOR_TOP_K
VECTOR_MIN_SCORE
```

`EMBEDDING_DIMENSION` 必须与真实 Embedding 返回维度及 pgvector column dimension 一致。

## 3. 本地执行步骤

### Step 1：准备真实 Provider

仅在未提交的 `backend/.env` 配置：

```dotenv
EMBEDDING_PROVIDER=openai-compatible
EMBEDDING_BASE_URL=<local-provider-endpoint>
EMBEDDING_API_KEY=<local-secret>
EMBEDDING_MODEL=<embedding-model>
EMBEDDING_DIMENSION=<actual-dimension>

VECTOR_PROVIDER=pgvector
VECTOR_DB_URL=<postgresql-async-url>
VECTOR_TOP_K=5
VECTOR_MIN_SCORE=0.0
```

### Step 2：启动基础设施

```powershell
docker compose up -d postgres redis
```

### Step 3：执行统一验证

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_phase_1_4_e_provider_validation.ps1
```

### Step 4：执行真实 Retrieval Scenario

使用现有 Knowledge Registry / ingestion / retrieval 场景，在同一 Knowledge Base scope 下完成 5 条 Dataset query。每条结果必须记录：

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
cd backend
uv run python scripts/evaluate_knowledge_retrieval_provider.py .\evaluation\vector_results.jsonl
```

门禁：

- Recall@K >= lexical-v2 baseline
- MRR >= lexical-v2 baseline
- provider error rate == 0
- Precision@K 作为观察指标
- latency 作为性能指标

## 4. 测试记录

截至本文创建时，代码库已经具备对应 contract tests、validation probes 和 quality-gate runner；本次 GitHub 开发环境**没有执行用户本地 PostgreSQL/pgvector/Embedding Provider**，因此真实 Provider 状态明确记录为：**待本地执行**。

用户此前反馈的本轮基础回归已经通过：

- Backend pytest：通过
- Frontend Vitest：通过
- Frontend build：通过

这些结果来自用户本地反馈，不由本次 GitHub 操作重新宣称执行。

## 5. 已知问题与解决方案

### 已知问题

1. GitHub 开发环境无法代替用户本地真实 Provider、数据库和 secret 环境，因此不能直接生成真实 vector evaluation evidence。
2. 当前没有自动后台索引队列，失败重建通过现有 API / 本地脚本触发。
3. 当前尚未实现跨 Version 的 `content_hash + embedding_model + embedding_dimension` embedding 复用。
4. Hybrid Retrieval 尚未进入实现。

### 解决方案

- 通过独立 provider-neutral contract 隔离真实供应商。
- 通过 Embedding / pgvector probe 提前发现环境问题。
- 通过统一 PowerShell suite 降低人工遗漏。
- Quality Gate 在缺少 `vector_results.jsonl` 时保持 pending，不把 skip 当作通过。
- 所有真实 secret 只放在未提交 `backend/.env`。

## 6. 下一阶段任务清单

| 优先级 | 任务 | 责任角色 | 前置依赖 | 目标时间 |
|---|---|---|---|---|
| **P0** | 完成真实 Embedding + pgvector 5 条 Dataset 端到端联调 | Backend / Knowledge | 本地 Provider、PostgreSQL/pgvector | 2026-08-20 |
| **P0** | 生成 `vector_results.jsonl` 并运行 Quality Gate | Backend / QA | P0 联调 | 2026-08-20 |
| **P0** | 根据 Recall/MRR/error/latency 结果决定是否修复 | Backend / Knowledge / QA | Quality Gate | 2026-08-21 |
| **P0** | 更新 Phase 1.4-E 最终验收与 `DEVELOPMENT.md` 状态 | Tech Lead | 评测结论 | 2026-08-21 |
| **P1** | 设计 Hybrid Retrieval contract | Architecture / Backend | Phase 1.4-E 通过 | 2026-08-24 |
| **P1** | 实现 hybrid scoring / rerank + evaluation | Backend / QA | Hybrid contract | 2026-08-26 |
| **P1** | 实现 Hybrid Retrieval Debug UI | Frontend | Hybrid API contract | 2026-08-27 |

## 7. 变更追踪

本检查点关联以下近期工程变更：

- Embedding batch size 配置：`1b43521e796dadaa7912f64379f72b40e052484c`
- Embedding provider contract / configuration：`9f3846a4d89d3edcfe6ac710fb8d27f08755ff91`
- pgvector indexing：`3092d83961521c025aea2daecb07f73be1c7aade`
- Embedding + pgvector indexing contract tests：`e5a8c63ccf52760fc8787d27f5112abbdd7996ef`
- 项目状态与追溯规范：`e4e4d6e3e62a9fdd38627704347dee052ccb2f42`
- 本检查点新增验证套件：本 Commit

## 8. 阶段退出条件

Phase 1.4-E 只有在以下条件全部满足后才能标记“完成”：

- [ ] 真实 Embedding Provider probe 通过。
- [ ] pgvector round-trip probe 通过。
- [ ] 5 条 Dataset 均完成真实 vector retrieval。
- [ ] `vector_results.jsonl` 已生成并经质量门禁验证。
- [ ] Recall@K / MRR 不低于 lexical-v2 baseline。
- [ ] provider error rate 为 0，或异常已有明确修复并重新验证。
- [ ] Backend pytest、Frontend npm test、Frontend npm run build 全部通过。
- [ ] 已知问题、解决方案、剩余风险全部记录。
- [ ] `DEVELOPMENT.md` 与阶段验收文档已同步更新。

在上述条件满足前，**不得进入 Hybrid Retrieval 的实现阶段**。
