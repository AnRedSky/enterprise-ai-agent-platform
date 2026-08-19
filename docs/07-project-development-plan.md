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
| Phase 1.5 | Workflow / Governance | **1.5-A 已验收；1.5-B Publish Governance / Tenant Contract 已通过本地手工验收；1.5-C Backend Contract 修复待本地验收** |

详细执行基线见 `docs/11-phase-1.4-knowledge-rag-plan.md`、`docs/12-phase-1.4-e-vector-retrieval-provider.md` 与 `docs/13-phase-1.5-workflow-governance-plan.md`。
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
更新验收文档
  ↓
直接提交 main
```

Backend 统一使用 uv 项目环境；Python、Alembic、pytest 以及脚本内 Python 命令必须通过 `uv run` 执行。Frontend 必须同时通过 `npm test` 与 `npm run build` 后才能进入下一模块。

## 7. 当前任务

**Phase 1.5-C Workflow Execution State Machine** 已完成 Backend Contract 实现，但本地验收曾被 Alembic metadata 兼容问题阻塞；问题已完成根因分析与代码修复，当前等待开发者本地重新验证。

当前实现范围：

1. 新增 `WorkflowExecution` / `WorkflowNodeExecution` domain。
2. 新增 Alembic `0016_workflow_execution_state_machine`。
3. Execution 状态：`pending → running → completed / failed / cancelled`。
4. Node 状态：`pending → running → completed / failed / skipped`。
5. 终态禁止再次转换。
6. Execution 与 Node Execution 均受 Tenant scope 约束。
7. 只能从当前 Workflow 的已发布版本创建 Execution。
8. 新增 Backend execution API contract 与独立 pytest。
9. 新增 Backend-only validation script：`backend/scripts/run_phase_1_5_c_workflow_execution_validation.ps1`。
10. 针对历史 `alembic_version.version_num VARCHAR(32)` 与新 revision id 长度不兼容的问题，增加 migration preflight 并新增单元测试。
11. **只有开发者本地验证通过后，才标记 1.5-C Backend 完成。**

开发者本地验证命令：

```powershell
cd backend
uv run alembic upgrade head
uv run alembic current
uv run pytest -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\run_phase_1_5_c_workflow_execution_validation.ps1
```

该脚本严格只执行 Backend migration / pytest，不调用 Frontend 测试；Frontend 必须独立执行 `npm test` 与 `npm run build`。

### 当前规则

- 本地开发 / 测试阶段，不执行 GitHub Actions CI。
- Backend 所有测试、脚本、Alembic 使用 `uv run` 项目环境。
- 真实 `.env` / API Key / DB credentials 不提交 Git。
- pgvector 必须由 PostgreSQL 服务端提供，不能通过 Python 依赖替代。
- Phase 1.5 必须严格遵循“Backend Contract → Migration/pytest → Frontend API/Vitest → UI → 手工验收 → 联调 → 全量回归 → 文档 → main”。
- Backend 测试脚本禁止混入 Frontend 测试；Frontend 测试必须独立通过 `npm test` / `npm run build` 执行。
- 工程错误统一记录到 `docs/error-tracking/`。
