# Phase 1.4 — Knowledge / RAG / Retrieval

## 1. 阶段目标

建立 Knowledge Registry、Document / Version / Chunk ingestion、Embedding / Retrieval contract、Runtime Knowledge integration、Citation 与 Retrieval Debug，并形成可测试的 Knowledge / Runtime 闭环。

## 2. 主要范围

- Knowledge Base / Document / Version Registry
- Document ingestion / cleaning / deterministic Chunk
- Chunk persistence 与 Version 关联
- Embedding / Retrieval Provider Contract
- Vector Retrieval
- Hybrid Retrieval
- Retrieval Debug
- Runtime Knowledge Context / Citation
- Knowledge 权限隔离
- Retrieval evaluation 与 Provider validation

## 3. Domain 边界

```text
Document
 ↓
Parser / Cleaner
 ↓
Chunker
 ↓
Embedding Provider
 ↓
Vector / Hybrid Retrieval
 ↓
Context Builder
 ↓
Runtime
 ↓
Citation / Audit / Observability
```

Knowledge/RAG 必须独立于 Agent Runtime；Provider 差异通过 Contract 封装。线上 Retrieval 不得使用 JSON/JSONL 结果文件替代数据库数据源。

## 4. 任务矩阵

| Task | 范围 | 历史状态归并 |
|---|---|---|
| 1.4-A | Knowledge Registry | 已完成；包含 metadata、Owner/RBAC、CRUD、分页、migration 0007、场景验收 |
| 1.4-B | Document ingestion | 已完成；包含 parser/cleaner、deterministic chunk、migration 0008、re-ingest、ingestion lifecycle |
| 1.4-C | Retrieval contract | 已完成；Embedding / Retriever / Reranker contract、provider-neutral result、lexical-v2 baseline |
| 1.4-D | Runtime Knowledge integration | 已完成当前历史范围；Knowledge config、Context Assembly、Citation、Observability、联调门禁 |
| 1.4-E | Retrieval productionization / Provider validation | 已完成当前代码范围；lexical-v2、evaluation、embedding adapter、pgvector、mock validation、vector retrieval。真实 Embedding Provider 语义质量仍以实际本地结果为准 |
| 1.4-F | Hybrid Retrieval | 已实现真实 DB orchestration、score fusion、quality evaluation |
| 1.4-G | Retrieval Debug / Runtime trace | G-01/G-02 已归并；来源/分数 breakdown、Runtime execution/trace 关联 |

## 5. 1.4-E 生产化深化

### 5.1 Retrieval baseline

历史 baseline 文档确认：Evaluation Dataset 与 Corpus 分离；ranking 必须来自生产 `lexical-v2` scoring；指标为 Recall@K / Precision@K / MRR；ranking 必须 deterministic（score 降序 + chunk_id 升序）。`knowledge_retrieval_baseline.json` 是评测产物，不是业务数据源。

### 5.2 Vector Provider

历史实现建立 provider-neutral `VectorRecord` / `VectorSearchResult` / provider error contract，并提供 deterministic in-memory contract adapter 与 PostgreSQL + pgvector adapter。`KnowledgeVectorIndexingService` 将 Chunk → Embedding → VectorRecord → pgvector；migration 0010/0011 分别负责 pgvector/chunk vector 表与 vector index status / embedding model。

Vector indexing 状态为 `pending / processing / ready / skipped / failed`。Chunk ingestion 与 vector indexing 分阶段，可独立失败和重试。真实 Provider 配置不得进入 Git。

### 5.3 Vector Retrieval API

`POST /api/v1/knowledge/retrieve` 支持 `mode=lexical-v2`、`mode=vector`，并支持显式 `fallback_to_lexical`。Vector/Embedding/pgvector/dimension 失败默认返回失败，不得静默改变 retrieval semantics；显式 fallback 时响应需标识 fallback。

### 5.4 Mock Embedding 边界

Mock Provider 为 deterministic token-hashing fixture，仅证明 Chunk → Embedding → pgvector → Retrieval → Evaluation 工程链路，不代表真实模型语义质量。历史问题记录显示中文连续文本特征不足曾导致 mock Quality Gate 失败，后通过中文 bigram 特征修复；该修复属于测试 fixture 特征构造，不得解释为真实 Embedding 质量结论。

### 5.5 Hybrid Retrieval

Hybrid 采用 lexical-v2 与 vector 两路真实服务结果进行 provider-neutral score fusion。默认 lexical/vector 权重为 0.5/0.5；同一 chunk 多来源时按规则融合，单来源候选不因缺失另一来源而人为降权；最终按稳定规则排序。Hybrid API 保留 `retrieval_mode`、`retrieval_sources`、citation、content、source URI 和 score breakdown。

## 6. 前端范围

Knowledge Base → Document → Version → Chunk 工作台；Retrieval Debug 支持 query / top-k / scope、loading、validation、error、empty result、Citation Detail、Source URI；G-01 增加 lexical/vector/hybrid 来源及 score breakdown；G-02 关联 Runtime execution / trace。

## 7. 数据与质量约束

Version 必须具备 ingestion 状态；Chunk 在 Version 内以 `chunk_index` 唯一且可追溯 `char_start / char_end`；`content_hash` 稳定；重复 ingestion 必须幂等；未经授权的用户不能读取其他 Owner 的 Version / Chunk。

Retrieval evaluation 至少记录 Recall@K、Precision@K、MRR、latency、provider error rate。质量门禁不得通过隐藏 provider error 提高成功率。

## 8. 历史验证脚本与实现追踪

历史 Phase 1.4 文档引用的主要验证入口已保留为代码事实：

- `backend/scripts/test/phase/1.4/run_phase_1_4_e_provider_validation.ps1`
- `backend/scripts/test/phase/1.4/run_phase_1_4_f_hybrid_quality_evaluation.ps1`
- `backend/scripts/test/phase/1.4/run_phase_1_4_f_retrieval_db_loop.ps1`
- `backend/scripts/test/phase/1.4/run_phase_1_4_g_01_retrieval_debug_validation.ps1`
- `backend/scripts/test/phase/1.4/run_phase_1_4_g_02_runtime_trace_validation.ps1`

## 9. 计划与实际结果分离

本文件保留 Phase 计划、任务边界、设计约束和历史任务归并；实际测试结果、验收结论和历史失败证据统一维护在 `docs/03-acceptance/PHASE_1_4_ACCEPTANCE.md`。未实际执行的命令不得写成通过。

## 10. 迁移来源

本 Phase 内容逐份核对并归并自：

- `11-phase-1.4-knowledge-rag-plan.md`
- `12-phase-1.4-e-retrieval-baseline.md`
- `12-phase-1.4-e-vector-retrieval-provider.md`
- `13-phase-1.4-e-vector-retrieval-validation.md`
- `13-phase-1.4-f-hybrid-retrieval.md`
- `14-phase-1.4-e-provider-validation-checkpoint.md`
- `15-phase-1.4-e-mock-embedding-validation.md`
- `phase-1.4-e-retrieval-evaluation-mock-embedding-fix-2026-08-19.md`
- `phase-1.4-e-retrieval-evaluation-runner-fix-2026-08-19.md`
- `PHASE_1_4_D_ACCEPTANCE.md`
- `PHASE_1_4_FG_ACCEPTANCE.md`

上述旧文档中的计划、边界、实现约束和历史问题已归并；实际验收证据见 Acceptance 文档。