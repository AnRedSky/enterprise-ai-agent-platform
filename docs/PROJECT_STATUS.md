# 项目开发进度

> 本文只记录项目任务进度、实际验收结果、阻塞项和下一步任务。工程开发规则统一维护在 `docs/DEVELOPMENT.md`。阶段计划维护在对应 `docs/PHASE_*.md`。

## 1. 当前主线

- 主分支：`main`
- 项目地址：`https://github.com/AnRedSky/enterprise-ai-agent-platform.git`
- 开发方式：所有功能直接在 `main` 开发与提交
- Phase 1.5：**已完成**
- Phase 1.6：**已完成并正式关闭**
- Phase 1.7：**已完成并正式关闭**
- 当前阶段：**Phase 1.8 Event / Webhook Trigger Expansion**
- 当前任务：**Phase 1.8-A 需求 / 架构确认已完成，准备进入 1.8-B Backend Contract**
- 当前角色：开发执行
- 测试 Gate 治理：Backend、Frontend、Browser/E2E 三层独立

## 2. 阶段状态

| 阶段 | 状态 | 说明 |
|---|---|---|
| Phase 1.0 | 已完成 | 工程初始化、FastAPI + Vue |
| Phase 1.2 | 已完成 | Identity、RBAC、Agent、Session、SSE、基础 Tool |
| Phase 1.3 | 已完成 | Model Gateway、Tool Runtime、Memory、Observability、基础管理端 |
| Phase 1.4 | 已完成核心闭环 | Knowledge / RAG、pgvector、Embedding / Retrieval contract、Runtime Trace |
| Phase 1.5 | **已完成** | Workflow / Governance A～G 全部完成；Circuit Breaker 最终验收通过 |
| Phase 1.6-A | **已完成** | Workflow Trigger Backend Contract；Backend Domain / API / Migration / Contract / Real API 两道 Gate 通过 |
| Phase 1.6-B | **已完成** | Frontend API Type / Vitest / Workflow Trigger Governance UI；Frontend Regression、Trigger Real HTTP、UI 手动验收通过 |
| Phase 1.6-C | **已完成** | Browser / Frontend-Backend E2E 第三独立测试层建立并通过；最终 Browser E2E 1 passed |
| Phase 1.6 | **已正式关闭** | A～C 全部完成，三层 Gate 与实际联调完成 |
| Phase 1.7-A | **已完成** | Scheduled Trigger Contract、Scheduler Runtime、bounded recovery、multi-worker slot convergence 基线审计与实现确认完成 |
| Phase 1.7-B | **已完成** | current/recovery persistence、idempotency、duplicate tick / restart、Runtime execution persistence 与 Real API 验收完成 |
| Phase 1.7-C | **已完成并关闭** | Schedule Governance Frontend API/UI Contract 完成；Frontend Regression Gate 通过 |
| Phase 1.7-D | **已完成并关闭** | Browser / Frontend-Backend E2E Scheduling Contract 完成；D-01～D-04 全部验收通过 |
| **Phase 1.7** | **已正式关闭** | A～D 全部完成；Backend、Frontend、Browser 三层 Gate 独立通过；Scheduler → Execution 真实边界完成验收 |
| **Phase 1.8-A** | **已完成** | Event / Webhook Trigger 需求、领域边界、Backend Contract 原则、Security / Idempotency、三层 Gate 已确认 |
| **Phase 1.8** | **进行中** | Event / Webhook Trigger Expansion；当前进入 1.8-B Backend Domain + API |

## 3. Phase 1.7-A/B 基线与 Runtime 结论

当前 main 已包含：

```text
Scheduled Trigger Contract
        ↓
FastAPI lifespan Scheduler
        ↓
interval slot
        ↓
deterministic idempotency key
        ↓
bounded recovery slots
        ↓
WorkflowExecutionService.create()
        ↓
workflow_executions persistence
        ↓
WorkflowExecutionService.run()
        ↓
completed / failed Execution
```

Scheduler 使用 PostgreSQL 数据库 unique constraint `(tenant_id, idempotency_key)` 作为同 slot 多 worker 的持久化收敛边界；只有实际成功完成 durable claim 的 worker 计为 dispatched，不增加并发旁路方案。

Phase 1.7-B 已完成并验证：

- current scheduled slot persistence；
- recovery slot persistence；
- deterministic idempotency key；
- duplicate tick / scheduler restart 不重复产生同 slot Execution；
- Real API 测试进程 AsyncEngine event-loop 生命周期治理；
- recovery 测试按 per-trigger persistence contract 断言；
- scheduler → workflow execution 的真实运行时边界。

## 4. Phase 1.7-C / D 与最终验收

Phase 1.7-C 已按既有 Backend Contract 完成前端 Schedule Governance Integration，未新增 Backend API、migration 或 Scheduler runtime implementation。

Phase 1.7-D 已完成真实 Browser → Vue → Backend HTTP → application scheduler → workflow execution 链路，并保持 Browser / Backend / Frontend 三层 Gate 独立。

最终验收结论：

- Phase 1.7-A：完成；
- Phase 1.7-B：完成；
- Phase 1.7-C：完成并关闭；
- Phase 1.7-D D-01：完成；
- Phase 1.7-D D-02：完成；
- Phase 1.7-D D-03：完成；
- Phase 1.7-D D-04：完成；
- Backend Gate：通过；
- Frontend Gate：通过；
- Browser / Frontend-Backend E2E Gate：通过；
- 无新增 migration；
- 无新增 Backend API contract；
- 无前端 scheduler 业务实现；
- 无跨层 Full Regression Gate；
- Phase 1.7：**正式关闭**。

## 5. Phase 1.8 需求 / 架构确认

> Phase 1.8 的具体主题并非历史文档中的既定事实。本阶段采用“Event / Webhook Trigger Expansion”作为基于已完成 Scheduled Trigger 能力的下一步工程方案，并已形成独立计划文档 `docs/PHASE_1_8.md`。

### 目标

将 Trigger 入口从时间驱动扩展为受治理的外部事件驱动入口：

```text
External Event
      ↓
Webhook / Event HTTP Contract
      ↓
Trigger Authentication / Validation
      ↓
Trigger Governance
      ↓
Deterministic Idempotency Claim
      ↓
Workflow Execution
      ↓
Trace / Audit / Observable Result
```

### 核心边界

- Webhook Trigger 与 Scheduled Trigger 共用 Trigger Domain / Workflow Execution Contract；
- Webhook 不重写 Scheduled Scheduler；
- 不引入 MQ/Kafka / 通用 Event Bus；
- 不允许任意代码执行；
- 重复事件必须通过数据库持久化唯一约束最终收敛；
- secret / token 不进入 AuditLog 或普通业务日志；
- Frontend 只消费 Backend Contract，不实现 runtime / idempotency / authentication。

### 任务状态

```text
1.8-A 需求 / Contract Baseline       ✅ 完成
1.8-B Backend Domain + API           ⏳ 下一步
1.8-C Frontend API + Governance UI   ⏳ 待 1.8-B
1.8-D Real API / Runtime Boundary    ⏳ 待 1.8-B
1.8-E Browser E2E                    ⏳ 待联调
1.8-F Final Acceptance               ⏳ 待完成
```

### 1.8-B 第一批实现任务

1. 审计现有 Trigger Model / Schema / Service；
2. 判断现有 Trigger / Execution 结构是否足以表达 Webhook；
3. 只有确有必要才新增 Alembic migration；
4. 定义 Webhook Trigger config contract；
5. 定义 Webhook endpoint 与统一响应 / error contract；
6. 定义 secret/header authentication contract；
7. 实现 durable idempotent execution claim；
8. 建立 unit → integration → api_contract → api_real 测试链路。

当前没有已知阻塞。实际测试结果在实现完成后记录，不预填通过。

## 6. 下一步

严格遵循 `docs/DEVELOPMENT.md` 固定顺序：

```text
1.8-B Backend Domain + API Contract
        ↓
Migration 判定 / 实施 + Backend tests
        ↓
1.8-C Frontend API Types + Vitest
        ↓
Frontend UI
        ↓
Real API Gate
        ↓
Backend Gate / Frontend Gate
        ↓
Frontend / Backend 联调
        ↓
1.8-E Browser E2E
        ↓
文档更新
        ↓
提交 main
```

当前责任角色：开发执行。
当前目标：完成 1.8-B Backend Contract 与 Migration 判定。
