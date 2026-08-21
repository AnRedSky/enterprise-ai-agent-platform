# Phase 1.4 — Acceptance

## 1. 验收范围

Knowledge Registry、Document / Version / Chunk ingestion、Runtime Knowledge integration、Retrieval、Citation、Knowledge / Retrieval Debug 前端，以及 Retrieval Provider validation。

## 2. 已读取的历史验收记录

- `PHASE_1_4_D_ACCEPTANCE.md`：Runtime + Knowledge 联调门禁，链路为 Auth → Knowledge Base → Document → Version → Ingest → AgentVersion Knowledge Config → Runtime Chat → Citation → Audit / Observability。
- `PHASE_1_4_FG_ACCEPTANCE.md`：Vue Knowledge / Retrieval Debug，包括 Knowledge 工作台、query/top-k/scope、loading/error/empty、Citation Detail / Source URI。

两者均归并到本 Phase Acceptance。

## 3. Acceptance Gate

- `uv sync`
- `uv run alembic upgrade head`
- `uv run pytest -q`
- Runtime Knowledge scenario
- `npm test`
- `npm run build`
- Retrieval / Provider validation scenarios

## 4. 核心 Contract

Version 必须有 ingestion lifecycle；Chunk 必须关联 `document_version_id`，`chunk_index` 在 Version 内唯一且从 0 递增，`char_start / char_end` 可追溯清洗文本，`content_hash` 稳定；重复 ingestion 不产生重复 Chunk；Owner / RBAC 隔离必须成立。

Retrieval 结果必须能够追溯 source document / chunk、score、citation 和 source URI。

## 5. 结果记录规则

旧文档中的“计划”“预期”“历史状态”不自动转化为当前通过结论。迁移完成后只将开发者实际反馈的测试结果写入本文。