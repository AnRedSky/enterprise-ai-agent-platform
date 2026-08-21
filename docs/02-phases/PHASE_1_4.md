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

Knowledge/RAG 必须独立于 Agent Runtime；Provider 差异通过 Contract 封装。

## 4. 任务拆解

历史记录包含 1.4-A/B/C/D/E/F/G 以及 E 阶段 Retrieval / Provider / Mock validation 等多个文件。迁移后统一在本 Phase 文档中以任务矩阵维护，不再使用连续数字文件名。

重点任务：

- Registry
- Ingestion / Chunk
- Runtime Knowledge integration
- Retrieval baseline
- Vector Retrieval Provider
- Vector Retrieval validation
- Hybrid Retrieval
- Provider validation checkpoint
- Mock Embedding validation
- Vue Knowledge / Retrieval Debug

## 5. 数据与质量

Version 必须具备 ingestion 状态；Chunk 在 Version 内以 `chunk_index` 唯一且可追溯 `char_start / char_end`；`content_hash` 稳定；重复 ingestion 必须幂等；未经授权的用户不能读取其他 Owner 的 Version / Chunk。

Retrieval evaluation 至少记录 Recall@K、Precision@K、MRR、latency、provider error rate。质量门禁不得通过隐藏 provider error 提高成功率。

## 6. 前端

Knowledge Base → Document → Version → Chunk 工作台；Retrieval Debug 支持 query / top-k / scope、loading、validation、error、empty result、Citation Detail 和 Source URI。

## 7. 验收

Phase 1.4 的历史 D、F/G Acceptance 记录统一并入 `03-acceptance/PHASE_1_4_ACCEPTANCE.md`。实际测试结果必须保留开发者真实反馈，不得根据旧计划推断通过。