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
| Phase 1.5 | Workflow / Governance | **基线已建立；1.5-A Backend Domain/API/Migration/pytest/手工验收实现进行中** |

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

## 7. 当前任务

**Phase 1.5-A Workflow Definition Contract** 已完成首轮代码落地，当前等待开发者本地 Backend 验证，不提前声明测试通过：

1. `Workflow` / `WorkflowVersion` Backend Domain 已建立。
2. `/api/v1/workflows` Registry / Version API 已建立。
3. Workflow owner/admin scope 已建立。
4. Workflow Version 唯一约束、生命周期字段与 Published 原地修改保护已建立。
5. Publish 写入现有 AuditLog contract。
6. Alembic `0013_workflow_definition` 已建立。
7. Backend-only 验收脚本：`backend/scripts/run_phase_1_5_a_workflow_registry_validation.ps1`。
8. **未执行的本地测试结果不写入项目状态；Tenant isolation 不宣称完成，因为当前 Identity 尚无 tenant contract。**

开发者本地验证命令：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_phase_1_5_a_workflow_registry_validation.ps1
```

该脚本严格只执行 Backend migration / pytest，不调用 Frontend 测试；Frontend 必须按准则独立执行 `npm test` 与 `npm run build`。

只有 Backend 验证通过后，才进入 Phase 1.5-A Frontend API Types / Vitest / UI。

### 当前规则

- 本地开发 / 测试阶段，不执行 GitHub Actions CI。
- Backend 所有测试、脚本、Alembic 使用 `uv run` 项目环境。
- 真实 `.env` / API Key / DB credentials 不提交 Git。
- pgvector 必须由 PostgreSQL 服务端提供，不能通过 Python 依赖替代。
- Phase 1.5 必须严格遵循“Backend Contract → Migration/pytest → Frontend API/Vitest → UI → 手工验收 → 联调 → 全量回归 → 文档 → main”。
- Backend 测试脚本禁止混入 Frontend 测试；Frontend 测试必须独立通过 `npm test` / `npm run build` 执行。
