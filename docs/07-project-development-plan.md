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
| Phase 1.5 | Workflow / Governance | **1.5-A Backend 验收通过；1.5-B Publish Governance 已验收；Tenant contract 已落地，等待本地 Backend 验收** |

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

**Phase 1.5-B Tenant Contract** 已完成首轮 Backend 代码落地，等待开发者本地 Backend 验证：

1. 新增 `Tenant` domain 与 `tenants` 表。
2. `User.tenant_id` / `Workflow.tenant_id` 建立非空 FK。
3. 新增 Alembic `0015_tenant_contract`，历史数据迁移到稳定 Default Tenant。
4. JWT access token 增加 `tenant_id` claim。
5. 登录 / 注册响应包含 `tenant_id`。
6. Workflow Registry 所有查询通过认证上下文执行 Tenant scope。
7. Admin 仅可跨 Owner 查询当前 Tenant，不获得跨 Tenant 能力。
8. Workflow API 不接受客户端提交 `tenant_id`。
9. 新增 Backend-only Tenant contract validation script：`backend/scripts/run_phase_1_5_b_tenant_contract_validation.ps1`。
10. **尚未写入本地测试结果；只有开发者本地验收通过后才标记 Tenant isolation 完成。**

开发者本地验证命令：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_phase_1_5_b_tenant_contract_validation.ps1
```

该脚本严格只执行 Backend migration / pytest，不调用 Frontend 测试；Frontend 必须按准则独立执行 `npm test` 与 `npm run build`。

只有 Tenant contract Backend 验证通过后，才进入 1.5-C Workflow Execution State Machine；Frontend Workflow API/UI 按固定前后端顺序进入后续任务。

### 当前规则

- 本地开发 / 测试阶段，不执行 GitHub Actions CI。
- Backend 所有测试、脚本、Alembic 使用 `uv run` 项目环境。
- 真实 `.env` / API Key / DB credentials 不提交 Git。
- pgvector 必须由 PostgreSQL 服务端提供，不能通过 Python 依赖替代。
- Phase 1.5 必须严格遵循“Backend Contract → Migration/pytest → Frontend API/Vitest → UI → 手工验收 → 联调 → 全量回归 → 文档 → main”。
- Backend 测试脚本禁止混入 Frontend 测试；Frontend 测试必须独立通过 `npm test` / `npm run build` 执行。
