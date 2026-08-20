# 项目开发规范核查与修正报告

> 核查基线：远端 `main` 最新代码与仓库现有 `docs/00-*`、`docs/DEVELOPMENT.md`、`docs/PROJECT_STATUS.md`、`docs/07-project-development-plan.md`、`docs/13-phase-1.5-workflow-governance-plan.md`。
>
> 本文只记录已经核查到的项目现状、规范一致性、历史偏差及修正后的执行基线；未实际执行的测试不标记为通过。

## 1. 核查结论

截至本次核查，项目已经形成较完整的企业级 AI Agent 平台第一阶段工程骨架，Phase 1.0、1.2、1.3、1.4 核心闭环以及 Phase 1.5-A～G 已在项目文档中记录为完成。Phase 1.5-G 已完成真实 PostgreSQL + HTTP Real API 验收，开发主线可以继续向后推进。

同时，历史开发过程中出现过两类会导致项目偏离系统要求的工程问题，已完成修正并纳入长期规则：

1. **Backend / Frontend 测试 Gate 曾发生跨技术栈耦合**：后端 release/full regression 脚本曾包含 Frontend 测试调用，违反前后端独立测试原则。现已拆分为 `backend/scripts/test/release/` 与 `frontend/scripts/test/release/`，并明确禁止恢复跨栈 Full Regression Gate。
2. **Circuit Breaker 真实链路暴露了数据库状态初始化与事务失败恢复问题**：新建状态对象在 SQLAlchemy flush 前计数值可能为 `None`，导致真实 API 返回 500；后续又暴露了失败事务继续复用同一 Session 的 `InFailedSQLTransactionError`。当前代码与文档已经围绕状态初始化、持久化 policy、Real API fixture 和治理边界完成修正，最终验收结果由 `PROJECT_STATUS.md` 记录。

本次核查不把“代码存在”直接等同于“生产能力完成”，后续工作必须继续按照 Contract → Migration/pytest → Frontend → Real API → 独立 Gates → 联调 → 文档 → main 的顺序推进。

## 2. 与系统建设目标的对照

| 系统要求 | 当前状态 | 核查结论 |
|---|---|---|
| FastAPI + Vue 分层工程 | 已建立 | 符合 |
| Identity / RBAC / Tenant | 已完成基础闭环 | 符合 Phase 1.x 基线 |
| Agent Runtime | 已建立并与 Workflow 集成 | 符合当前阶段边界 |
| Model Gateway | 已完成基础能力 | 后续继续 Provider 生产化 |
| Tool Runtime | 核心能力已完成 | 后续继续生产化治理 |
| Memory | 核心能力已完成 | 后续继续生产化治理 |
| Knowledge / RAG | 核心闭环已完成 | 后续继续真实 Provider / 质量深化 |
| Observability / Audit / Trace | 核心链路已完成 | Workflow 治理已接入 |
| Workflow Definition / Version / Publish | 已完成 | 符合 Phase 1.5-A/B |
| Workflow Execution State | 已完成 | 符合 Phase 1.5-C |
| Runtime Integration | 已完成 | 符合 Phase 1.5-D |
| Governance / Audit / Trace | 已完成 | 符合 Phase 1.5-E |
| Retry / Timeout / Deadline / Idempotency / Concurrency | 已完成 | 符合 Phase 1.5-F |
| Circuit Breaker | 已完成 | 符合 Phase 1.5-G |
| 高并发 MQ / Worker / 分布式编排 | 未实现 | 原计划明确暂不实现，不属于当前缺陷 |
| Temporal 等具体 Workflow Engine | 未实现 | 原计划明确暂不绑定 |
| 多 Agent 协作 | 未形成完整生产闭环 | 后续阶段 |
| Evaluation | 后续阶段 | 不应提前标记完成 |
| Browser / Frontend-Backend E2E | 当前未实现 | 必须作为独立第三测试层规划 |

系统总体架构要求 Workflow、Agent Runtime、Tool、Knowledge、Memory、Model Gateway、Governance 等领域解耦；当前 Phase 1.5 计划与该边界保持一致。

## 3. 工程开发规则核查

### 3.1 主分支规则

当前开发准则要求所有开发直接基于远端 `main`，禁止创建功能分支、临时分支或长期开发分支。后续所有代码、测试、migration、文档修正继续直接提交 `main`。

### 3.2 Backend / Frontend 测试必须完全独立

当前规则已经明确：

```text
Backend
backend/tests/
backend/scripts/test/

Frontend
frontend/tests/
frontend/scripts/test/

Browser / Frontend-Backend E2E
未来作为第三独立层
```

Backend Gate 只负责：

```text
uv run pytest -q
→ alembic upgrade head
→ Real HTTP API Gate
```

Frontend Gate 只负责：

```text
npm test
→ npm run build
```

禁止出现一个脚本同时调用 `uv run pytest` 与 `npm test` / `npm run build`。该规则已写入 `DEVELOPMENT.md`、`PROJECT_STATUS.md` 与 Phase 1.5 计划。

### 3.3 Backend 脚本目录归属

Backend release gate、Real API gate 和其他 Backend 编排脚本必须位于 `backend/scripts/`；Frontend gate 必须位于 `frontend/scripts/`。不得把 Frontend 脚本放入 Backend，也不得由 Backend gate 间接启动 Frontend。

### 3.4 测试结果真实性

文档只能记录实际执行结果。Architecture / Plan 文档中的“完成”表示该计划项已经完成相应开发与验收闭环；对于下一阶段尚未执行的内容必须明确标记为待执行、候选或阻塞，不得提前写“通过”。

## 4. 当前项目完成度判断

### 已形成稳定基线

- 工程初始化与 FastAPI + Vue 技术栈。
- Identity / RBAC / Tenant 基础治理。
- Agent / Session / SSE 基础能力。
- Model Gateway、Tool Runtime、Memory、Observability 核心能力。
- Knowledge / RAG 核心闭环及 pgvector / Retrieval contract。
- Workflow Definition / Version / Publish / Tenant / Execution / Runtime / Governance。
- Workflow Reliability：Cancel、Retry、Retry lineage、Idempotency-Key、Concurrency、Timeout、Failure Recovery、Retry Budget、Workflow Deadline。
- Circuit Breaker：CLOSED / OPEN / HALF_OPEN、持久化 Policy、Tenant isolation、Policy drift、Fast-Fail、Probe quota、恢复与失败重开。
- Backend / Frontend 测试 Gate 独立治理。

### 尚不能视为完整生产级能力

根据总体架构文档与 Phase 1.5 的明确范围，以下能力仍属于后续建设：

- 分布式 Worker / MQ / 异步编排。
- 高级 DAG 调度。
- 多 Agent Supervisor / Planner / Worker / Reviewer 协作闭环。
- Saga / 自动补偿。
- Cron / Event Trigger 全套能力。
- 复杂 Policy DSL 与生产级审批中心。
- Workflow 可视化拖拽编辑器。
- Evaluation 体系的完整生产化闭环。
- Browser / Frontend-Backend E2E 独立测试层。
- 更完整的限流、降级、流量控制、成本治理和生产运维能力。

这些项目不能因为 Phase 1.5 完成而提前标记为完成。

## 5. 修正后的后续推进原则

Phase 1.5-G 已完成，不再继续重复开发 Circuit Breaker。下一步必须先做“后续阶段范围确认”，避免直接从聊天上下文跳到具体实现。

### 下一阶段启动前置任务

1. 以总体架构文档为上位目标，盘点当前已实现能力与未实现能力。
2. 为下一阶段建立单独 Phase 计划文档，明确 Domain Contract、API、Migration、测试 Gate、验收门禁和不做范围。
3. 优先选择能够形成业务闭环且不依赖尚未建设的分布式基础设施的任务。
4. 仍严格执行 Backend-first；Frontend 不得先于 Backend Contract。
5. Real API、Frontend Gate、Backend Gate 必须继续独立。
6. 每个已经发生的工程错误继续写入 `docs/error-tracking/`。
7. 完成后直接提交 `main`，并同步 `PROJECT_STATUS.md`。

### 下一阶段候选优先级

| 优先级 | 候选方向 | 原因 | 当前状态 |
|---|---|---|---|
| P0 | Workflow Production Hardening / Trigger Contract | 在现有 Workflow 核心闭环上继续形成可复用业务入口，且可保持单体 PostgreSQL/FastAPI 边界 | 待建立 Phase Contract |
| P1 | Evaluation 基础 Contract | 总体架构明确包含 Evaluation，且后续模型/Agent 质量治理需要统一评测接口 | 待规划 |
| P1 | Multi-Agent Orchestration Contract | 总体目标包含多 Agent 协作，但应先定义领域边界再实现 | 待规划 |
| P2 | Distributed Worker / MQ | 需要更完整基础设施与部署边界，不应在当前阶段无 Contract 直接实现 | 暂缓 |
| P2 | Browser E2E | 必须作为第三独立测试层建设，不能并入 Backend/Frontend Gate | 暂缓 |

> 本表是核查后的规划建议，不把候选项误写成既有项目正式 Phase。正式开始下一阶段代码开发前，必须先形成对应 Phase 计划并提交 `main`。

## 6. 验收与追踪要求

每个后续任务至少必须留下：

```text
需求 / 架构依据
↓
Backend Contract
↓
Migration（如涉及 DB）
↓
Backend pytest
↓
Frontend API Type / Vitest / UI（如涉及前端）
↓
Real API / 手工验收
↓
Backend Gate（独立）
Frontend Gate（独立）
↓
联调 / E2E（若该阶段定义）
↓
PROJECT_STATUS / Phase 文档 / error-tracking
↓
main
```

本报告用于纠偏与后续开发跟踪；它不替代 `DEVELOPMENT.md` 的长期工程规则，也不替代具体 Phase 计划。
