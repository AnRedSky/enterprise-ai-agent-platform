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
| Phase 1.4-A | Knowledge Registry | 本地手工验收通过 |
| Phase 1.4-B | Document ingestion / Chunk | Backend contract、migration、chunk persistence、API、pytest、手工脚本验收通过 |
| Phase 1.4-C | Retrieval contract | lexical-v2 核心检索与质量门禁已通过 |
| Phase 1.4-D | Runtime Knowledge integration | Auth → Knowledge → Ingest → AgentVersion → Runtime Chat → Citation 联调通过 |
| Phase 1.4-E | Knowledge / Retrieval 生产化深化 | **pgvector schema、adapter、Embedding Provider contract、真实 Chunk → Embedding → pgvector indexing 链路已实现；待本地真实 Embedding 配置后验收** |
| Phase 1.4-F/G | Vue Knowledge / Retrieval Debug | 进行中 |
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

**Phase 1.4-E → Vector Retrieval API 闭环**：

1. 本地执行 `uv run alembic upgrade head`，确认 migration 0011。
2. 运行 vector / indexing contract tests。
3. 如配置真实 Embedding，执行 `scripts/run_embedding_provider_validation.ps1`。
4. 设置 `VECTOR_PROVIDER=pgvector` 后，通过 Knowledge ingest 验证 `Chunk → Embedding → pgvector upsert`，检查 `vector_index_status=ready`。
5. Retrieval API 增加 `mode=vector`，保持 lexical-v2 不变。
6. 使用现有 Evaluation Dataset 对 lexical-v2 / vector retrieval 做 Recall@K、Precision@K、MRR 对比。
7. 稳定后进入 hybrid retrieval。

### 当前规则

- 本地开发 / 测试阶段，不执行 GitHub Actions CI。
- Backend 所有测试、脚本、Alembic 使用 `uv run` 项目环境。
- 真实 `.env` / API Key / DB credentials 不提交 Git。
- pgvector 必须由 PostgreSQL 服务端提供，不能通过 Python 依赖替代。
