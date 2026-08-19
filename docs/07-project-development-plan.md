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
| Phase 1.4-E | Knowledge / Retrieval 生产化深化 | pgvector schema、adapter、Embedding Provider contract、真实 Chunk → Embedding → pgvector indexing 链路已实现；mock + PostgreSQL/pgvector deterministic quality validation 已通过；真实 Embedding 语义质量仍待真实 Provider |
| Phase 1.4-F/G | Vue Knowledge / Retrieval Debug / Runtime Trace | **G-01 / G-02 已完成；Backend 152 passed、0 warnings；migration 0012 已到 head** |
| Phase 1.5 | Workflow / Governance | **开发基线已建立；1.5-A Workflow Definition Contract Ready** |

详细执行基线见 `docs/11-phase-1.4-knowledge-rag-plan.md`、`docs/12-phase-1.4-e-vector-retrieval-provider.md` 与 `docs/13-phase-1.5-workflow-governance-plan.md`。

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

**Phase 1.5-A Workflow Definition Contract**：

1. 建立 Workflow / WorkflowVersion Backend Domain。
2. 明确 Workflow 生命周期、Version 不可变与 Publish 规则。
3. 建立 `/api/v1/workflows` Registry / Version API contract。
4. 建立 tenant / owner isolation 与 Admin scope contract。
5. 完成 Alembic migration + Backend pytest + Backend 独立手工验收脚本。
6. Backend 通过后才进入 Frontend API Types / Vitest / UI。

详细范围、状态机、字段、API、RBAC、验收门禁见 `docs/13-phase-1.5-workflow-governance-plan.md`。

### 当前规则

- 本地开发 / 测试阶段，不执行 GitHub Actions CI。
- Backend 所有测试、脚本、Alembic 使用 `uv run` 项目环境。
- 真实 `.env` / API Key / DB credentials 不提交 Git。
- pgvector 必须由 PostgreSQL 服务端提供，不能通过 Python 依赖替代。
- Phase 1.5 必须严格遵循“Backend Contract → Migration/pytest → Frontend API/Vitest → UI → 手工验收 → 联调 → 全量回归 → 文档 → main”。
- Backend 测试脚本禁止混入 Frontend 测试；Frontend 测试必须独立通过 `npm test` / `npm run build` 执行。
