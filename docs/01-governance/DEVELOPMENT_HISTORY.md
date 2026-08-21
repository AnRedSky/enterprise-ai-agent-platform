# 历史开发与环境基线

> 本文用于承接旧根级连续编号文档中的工程历史。它不是当前规则入口；当前长期规则以 `DEVELOPMENT.md` 为准，当前项目状态以 `PROJECT_STATUS.md` 为准。

## 1. 项目初始化

旧 `01-project-initialization.md` 确认技术路线：FastAPI + Python、Vue 3 + TypeScript + Vite、PostgreSQL、Redis、Alembic、pytest、GitHub Actions，并形成 API / Service / Runtime / Gateway/Tool/Memory / Repository 分层。早期 Phase 1 目标是单 Agent、单模型、基础 Tool MVP，随后进入 Phase 1.2。

## 2. Phase 1.2 基础平台

旧 `02-phase-1.2-foundation.md` 记录 User/Role/UserRole、JWT/RBAC、Agent/AgentVersion、Session/Message、SSE Runtime、Model Gateway、Mock/OpenAI-compatible Provider、Tool/AgentTool Registry、AuditLog、Alembic、pytest、CI、Vue 管理端和 Docker Compose 基础结构。

历史记录中曾使用 `feature/phase-1.2` 分支；该规则已废止，当前唯一开发基线为 `main`，历史分支名称只作为历史事实保留。

## 3. CI / Main 基线历史

旧 `08-ci-pause-and-main-baseline.md` 记录过 CI 暂停和 main 基线切换。原记录没有可复现的历史失败 Job 日志，因此明确没有虚构错误信息。后续项目规则进一步明确：本项目验收以本地 Backend / Frontend / Browser Gate 为准，不能把 GitHub Actions 状态作为验收依据。

## 4. Memory Runtime / Governance

旧 `09-memory-runtime-integration.md` 记录 MemoryContextBuilder 将 MemoryService 接入 Agent Chat Runtime：System Prompt → Memory Context → Session History → Current User Input；`memory_limit` 1-50、默认字符上限 6000，并以 user/agent/session 隔离。

旧 `10-memory-governance.md` 和 `11-memory-governance-completion.md` 记录 `is_active`、`expires_at`、0003 migration、get/update/delete、expired/inactive filtering，以及明确当时尚未宣称完整 HTTP CRUD API 已完成。

## 5. Observability 第一版

旧 `12-observability.md` 与 `13-observability-completion.md` 记录 Execution / ExecutionEvent、0004 migration、ObservabilityService、Runtime lifecycle、Model Call span、request/trace/execution 关联、token usage、latency/status/error。敏感信息不得写入 Observability。后续 Tool span、Memory span、查询 API、Vue Observability、OpenTelemetry 等按阶段逐步演进。

## 6. Repository / Environment

旧 `12-project-repository-and-environment.md` 明确 Backend 使用 uv，Python/Alembic/pytest 使用 `uv run`；Frontend 使用 Node/npm，`npm test` 与 `npm run build` 独立执行；`.env`、`.venv`、node_modules、dist、coverage 等不得提交。

## 7. 历史下一步基线

旧 `13-next-step-baseline.md` 曾将 Runtime + Knowledge 联调列为当前下一步，并要求 Backend uv、Alembic、pytest、Runtime Knowledge Scenario、Frontend test/build、联调和文档更新。该内容已被后续 Phase 1.4 文档和 Acceptance 取代，不再作为当前状态。

## 8. 测试脚本治理历史

旧 `11-testing-script-governance.md` 建立了 unit/integration/api_contract/api_real 四层 Backend 测试目录和 scripts/test、evaluation、dev 职责。其“Full Regression 包含 Frontend”部分后来与当前独立 Gate 规则冲突，冲突内容不继承；当前规则以 `DEVELOPMENT.md` / `LOCAL_TESTING.md` 为准。

## 9. 规范核查历史

旧 `14-project-compliance-audit-and-correction-plan.md` 记录过 Backend/Frontend Gate 耦合、Circuit Breaker 数据初始化/事务恢复等纠偏，并强调 Contract → Migration/pytest → Frontend → Real API → 独立 Gate → 联调 → 文档 → main 的追溯链。该纠偏原则保留，旧候选 Phase 计划不作为当前状态。

## 10. 来源

- `01-project-initialization.md`
- `02-phase-1.2-foundation.md`
- `07-project-development-plan.md`
- `08-ci-pause-and-main-baseline.md`
- `09-memory-runtime-integration.md`
- `10-memory-governance.md`
- `11-memory-governance-completion.md`
- `11-testing-script-governance.md`
- `12-observability.md`
- `12-project-repository-and-environment.md`
- `13-next-step-baseline.md`
- `13-observability-completion.md`
- `14-project-compliance-audit-and-correction-plan.md`

## 11. 规则优先级

历史记录不得覆盖：

1. `01-governance/DEVELOPMENT.md`
2. `01-governance/DOCUMENTATION.md`
3. `PROJECT_STATUS.md`
4. 当前 `02-phases/PHASE_x_y.md`
5. 当前 `03-acceptance/PHASE_x_y_ACCEPTANCE.md`
