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
| Phase 1.5 | Workflow / Governance | **1.5-A～1.5-G 全部完成；1.5-G Circuit Breaker Real API 已完成最终验收** |
| Phase 1.6 | Workflow Production Hardening | **A～C 全部完成并正式关闭；Backend / Frontend / Browser E2E 三层 Gate 与实际联调完成** |
| Phase 1.7-A | Scheduled Trigger Backend Contract | **开发中** |
| Phase 1.7-B | Scheduler execution / persistence integration | 待 1.7-A 验收 |
| Phase 1.7-C | Frontend Schedule Governance UI Contract | 待 1.7-B |
| Phase 1.7-D | Real HTTP + Browser E2E scheduling contract | 待 1.7-C |

详细执行基线见 `docs/11-phase-1.4-knowledge-rag-plan.md`、`docs/12-phase-1.4-e-vector-retrieval-provider.md`、`docs/13-phase-1.5-workflow-governance-plan.md`、`docs/15-phase-1.6-workflow-production-hardening-plan.md` 与 `docs/18-phase-1.7-workflow-trigger-scheduling-contract.md`。
当前项目实时进度统一见 `docs/PROJECT_STATUS.md`；工程长期开发规则统一见 `docs/DEVELOPMENT.md`。

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
Browser E2E（需要时作为第三独立层）
  ↓
更新验收文档
  ↓
直接提交 main
```

Backend 统一使用 uv 项目环境；Python、Alembic、pytest 以及脚本内 Python 命令必须通过 `uv run` 执行。Frontend 必须同时通过 `npm test` 与 `npm run build` 后才能进入下一模块。

## 7. Phase 1.6 最终关闭记录

Phase 1.6 已完成：

1. Workflow Trigger Backend Contract。
2. Trigger CRUD / invoke / lifecycle / Published Workflow validation。
3. Idempotency / Concurrency / Reliability Governance 复用。
4. Audit / Trace Trigger identity。
5. Frontend Trigger API Type / Vitest / Governance UI。
6. Trigger Real HTTP contract 与 UI 手工验收。
7. 第三独立 Browser E2E 层。

最终开发者本地验收：

```text
Backend Real API
→ 14 passed in 21.28s

Frontend Vitest
→ 50 passed

Frontend production build
→ PASS

Browser E2E
→ 1 passed (3.9s)
```

Phase 1.6 正式关闭。

## 8. Phase 1.7 当前基线

Phase 1.7 是项目在 Phase 1.6 manual Trigger 业务入口闭环之后的下一项能力扩展。当前只推进 Scheduled Trigger Backend Contract，不提前引入 Scheduler 基础设施。

第一项任务：**Phase 1.7-A-01 Scheduled Trigger Backend Contract**。

初始 Schedule Contract 采用可测试的：

```json
{
  "timezone": "Asia/Shanghai",
  "interval_seconds": 300
}
```

第一项任务明确不实现 MQ、Worker、Event Bus、Cron daemon、Temporal/Airflow 或任意 Cron DSL。保存 Schedule 不产生 Workflow Execution。

## 9. 当前规则

- 本地开发 / 测试阶段，不执行 GitHub Actions CI。
- Backend 所有测试、脚本、Alembic 使用 `uv run` 项目环境。
- 真实 `.env` / API Key / DB credentials 不提交 Git。
- pgvector 必须由 PostgreSQL 服务端提供，不能通过 Python 依赖替代。
- Backend Regression Gate 与 Frontend Regression Gate 必须分别位于 `backend/` 与 `frontend/` 目录。
- Real API 唯一入口为 `backend/scripts/test/api-real/01_run_real_api_tests.ps1`。
- Browser / Frontend-Backend E2E 作为第三独立测试层维护在 `frontend/scripts/test/e2e/`。
- 工程错误统一记录到 `docs/error-tracking/`。

## 10. 下一步任务

立即进入 **Phase 1.7-A-01 Scheduled Trigger Backend Contract**：先实现 Domain / Schema Contract 与 pytest/API Contract；完成 Backend Contract 后再进入 migration、Real API 与 Frontend，不得跳过 Backend Contract 直接开发调度 UI。
