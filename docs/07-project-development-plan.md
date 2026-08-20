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
| Phase 1.6 | Workflow Production Hardening | **已建立阶段基线；下一项为 1.6-A Workflow Trigger Contract，尚未开始代码实现** |

详细执行基线见 `docs/11-phase-1.4-knowledge-rag-plan.md`、`docs/12-phase-1.4-e-vector-retrieval-provider.md`、`docs/13-phase-1.5-workflow-governance-plan.md` 与 `docs/15-phase-1.6-workflow-production-hardening-plan.md`。
当前项目实时进度统一见 `docs/PROJECT_STATUS.md`；工程长期开发规则统一见 `docs/DEVELOPMENT.md`；规范核查与纠偏见 `docs/14-project-compliance-audit-and-correction-plan.md`。

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

## 7. Phase 1.5-G Circuit Breaker Real API 完成记录

Phase 1.5-G 已完成以下能力：

1. `WorkflowCircuitState` 持久化模型。
2. `0020_workflow_circuit_breaker` 基础表迁移。
3. `0021_workflow_circuit_policy` 持久化 `failure_threshold` / `recovery_timeout_ms` / `half_open_max_calls`。
4. Database-backed `CircuitBreakerService`。
5. CLOSED / OPEN / HALF_OPEN 状态机。
6. `tenant_id + circuit_key` 隔离。
7. OPEN Fast-Fail，`CIRCUIT_OPEN` 不进入 Node Retry。
8. HALF_OPEN probe quota 并发治理。
9. probe success → CLOSED；probe failure → OPEN。
10. policy drift 返回 `409`，禁止静默改变既有治理参数。
11. Retry / Timeout / Workflow Deadline / Governance 边界。
12. Real API deterministic fixture 与并发 HALF_OPEN probe 场景。
13. 修复 Circuit State 新建对象在 SQLAlchemy flush 前计数值可能为 `None` 的初始化缺陷。

开发者本地验收结果：

```text
uv run alembic upgrade head
→ 0020_workflow_circuit_breaker -> 0021_workflow_circuit_policy 成功

uv run pytest -q
→ 209 passed, 11 deselected in 3.44s

powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
→ 11 passed in 17.62s
→ [PASS] Real API gate completed. Frontend/backend integration may proceed.
```

Phase 1.5-G 最终验收通过，Phase 1.5 正式关闭。

## 8. 当前规则

- 本地开发 / 测试阶段，不执行 GitHub Actions CI。
- Backend 所有测试、脚本、Alembic 使用 `uv run` 项目环境。
- 真实 `.env` / API Key / DB credentials 不提交 Git。
- pgvector 必须由 PostgreSQL 服务端提供，不能通过 Python 依赖替代。
- Phase 1.5 必须严格遵循“Backend Contract → Migration/pytest → Frontend API/Vitest → UI → 手工验收 → 联调 → 全量回归 → 文档 → main”。Phase 1.6 继续执行相同固定顺序。
- Backend 测试脚本禁止混入 Frontend 测试；Frontend 测试必须独立通过 `npm test` / `npm run build` 执行。
- Backend Regression Gate 与 Frontend Regression Gate 必须分别位于 `backend/` 与 `frontend/` 目录。
- Real API 唯一入口为 `backend/scripts/test/api-real/01_run_real_api_tests.ps1`。
- 不得恢复同时调用 Backend 与 Frontend 测试的 Full Regression 脚本。
- 工程错误统一记录到 `docs/error-tracking/`。

## 9. 下一步任务

Phase 1.5 已正式完成。下一阶段为 **Phase 1.6 Workflow Production Hardening**，当前第一项执行任务为 **1.6-A Workflow Trigger Contract**。必须先完成 Backend Contract，再按固定前后端顺序推进；不得直接实现 MQ、Worker、Cron、Event Bus 或具体 Workflow Engine。
