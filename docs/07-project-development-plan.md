13. Evaluation（后续阶段）

## 5. 开发阶段计划

| 阶段 | 内容 | 状态 |
|---|---|---|
| Phase 1.0 | 工程初始化、FastAPI + Vue | 已完成 |
| Phase 1.2 | Identity、RBAC、Agent、Session、SSE、基础 Tool | 已完成 |
| Phase 1.3-A | Model Gateway | 已完成 |
| Phase 1.3-B | Tool Runtime | 核心能力已完成；后续继续生产化治理 |
| Phase 1.3-C | Memory | 核心能力已完成；后续继续生产化治理 |
| Phase 1.3-D | Observability | 核心执行链路已完成 |
| Phase 1.3-E | Vue 管理端深化 | 基础管理闭环已完成 |
| Phase 1.4-A | Knowledge Registry | **本地手工验收通过：CRUD、Version、分页、删除、Owner/RBAC 闭环通过** |
| Phase 1.4-B | Document ingestion / Chunk | **Backend contract / migration / parser-cleaner / deterministic chunk / persistence / API / pytest / 手工脚本已提交；本地迁移与回归验收通过** |
| Phase 1.4-C | Retrieval contract | **核心检索服务已实现；本地 pytest + Retrieval 手工验收通过** |
| Phase 1.4-D | Runtime Knowledge integration | **联调门禁已建立；Auth → Knowledge → Document → Version → Ingest → AgentVersion → Runtime Chat → Citation → Audit/Observability 已完成本地回归** |
| Phase 1.4-E | Knowledge / Retrieval 生产化深化 | **lexical-v2、Evaluation Dataset、Recall/Precision/MRR quality gate、OpenAI-compatible Embedding Provider、Vector Retrieval provider-neutral contract、PostgreSQL + pgvector adapter、0010 migration、scope/dimension contract 已完成；等待本地 PostgreSQL + pgvector round-trip 验收** |
| Phase 1.4-F/G | Vue Knowledge / Retrieval Debug | **进行中：Knowledge Workbench、Retrieval Debug、检索 loading/error/empty、结果与 Citation Detail 已落地；继续补齐 Runtime execution 关联与浏览器验收** |
| Phase 1.5 | Workflow / Governance | 后续 |

详细执行基线见 `docs/11-phase-1.4-knowledge-rag-plan.md` 与 `docs/12-phase-1.4-e-vector-retrieval-provider.md`。

## 6. 固定前后端开发顺序

所有功能必须严格执行：

```text
需求 / 架构文档确认
  ↓
Backend Domain + API Contract
  ↓
Backend pytest / API Scenario
  ↓
Frontend API Client + Type
  ↓
Frontend Vue UI
  ↓
Frontend Vitest
  ↓
Frontend production build
  ↓
前后端实际联调
  ↓
更新验收文档
  ↓
直接提交 main
```

Backend 统一使用 uv 项目环境；Python、Alembic、pytest 以及脚本内 Python 命令必须通过 `uv run` 执行。Frontend 必须同时通过 `npm test` 与 `npm run build` 后才能进入下一模块。

## 7. 当前下一任务

**Phase 1.4-E → 真实 Embedding → pgvector indexing / vector retrieval 闭环**：

1. 本地 PostgreSQL 执行 migration 0010，确认 pgvector extension、table、HNSW index。
2. 执行 pgvector round-trip probe，确认 upsert、cosine search、Knowledge Base scope、cleanup。
3. 将真实 Embedding Provider 接入 Document Chunk indexing，建立 Chunk → Embedding → pgvector upsert 链路。
4. Retrieval API 增加 vector retrieval mode，并保留 lexical-v2。
5. 使用现有 5 条 Evaluation Dataset 对 lexical-v2 / vector retrieval 做 Recall@K、Precision@K、MRR 对比。
6. vector retrieval 稳定后进入 hybrid retrieval（lexical + vector）。

当前阶段不执行 GitHub Actions CI；测试由本地 `uv run` 环境执行并由开发者反馈结果。
