# 项目开发进度

> 本文只记录项目任务进度、实际验收结果、阻塞项和下一步任务。工程开发规则统一维护在 `docs/DEVELOPMENT.md`。

## 1. 当前主线

- 主分支：`main`
- 项目地址：`https://github.com/AnRedSky/enterprise-ai-agent-platform.git`
- 开发方式：所有功能直接在 `main` 开发与提交
- Phase 1.5：**已完成**
- Phase 1.6：**已完成并正式关闭**
- 当前阶段：**Phase 1.7 Workflow Trigger Expansion / Scheduling Contract**
- 当前任务：**Phase 1.7-B Scheduler execution / persistence integration**
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
| Phase 1.7-A | **基线审计完成** | A-01 Contract、A-02 Scheduler Runtime、A-03 bounded recovery、A-04 multi-worker slot convergence 已存在于最新 main；不重复实现 |
| Phase 1.7-B | **开发中 / Gate 待重新执行** | Persistence contract 已收口；recovery persistence Real API 已加入；AsyncEngine event loop 生命周期问题已在测试层修复；本轮进一步修正 recovery 测试对全局 scheduler counters 的错误假设；Runtime failure 专项验收仍未完成 |

## 3. Phase 1.7-A 基线审计结论

远端 `main` 最新基线已包含：

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
recovery audit / trace
        ↓
WorkflowExecutionService.create()
        ↓
workflow_executions persistence
        ↓
WorkflowExecutionService.run()
        ↓
completed / failed Execution
```

因此，原文档中“1.7-A 尚未实现 Scheduler / Worker”的描述已经过时，不能继续作为开发基线。

同时确认当前 Scheduler 已采用 PostgreSQL transaction-scoped advisory lock 配合既有 `(tenant_id, idempotency_key)` unique constraint 作为同 slot 多 worker 的数据库收敛边界。本阶段不再增加并发旁路方案。

## 4. Phase 1.7-B 当前实施范围

Phase 1.7-B 不重新实现 Scheduler，而是验证并收口现有真实执行与持久化链路：

1. Scheduled slot 创建唯一 Execution。
2. Execution `pending` 持久化后进入 Runtime。
3. Runtime 成功后持久化 `completed`。
4. Runtime 失败后持久化 `failed`，不能丢失 Execution。
5. Recovery 与普通 scheduled execution 使用同一 persistence boundary。
6. Scheduler restart / duplicate tick 不产生第二条同 slot Execution。
7. Execution 的 `idempotency_key`、`scheduled_slot`、`recovery` 可以解释调度来源。
8. Audit / Trace 与 Execution 状态保持一致。

当前阶段原则：**真实数据库优先，不使用 JSON fixture 替代数据库业务状态。**

### 已完成的代码工作

- 明确并记录 `workflow_executions` 为 Scheduled Trigger execution persistence boundary。
- 保持现有 scheduler / idempotency / advisory-lock 实现，不增加并发旁路方案。
- Real API 已直接查询 PostgreSQL `workflow_executions`，验证 current slot 的 `status / idempotency_key / input_data`。
- 新增 recovery persistence Real API contract：验证 recovery slot 与 current slot 均落入同一 `workflow_executions` persistence boundary，并验证重复 tick / scheduler restart 不产生重复记录。
- 修复 Real API 测试本身的 AsyncEngine event loop 生命周期问题：scheduler direct-call contract 现在在 module-scoped event loop 内执行，并在 loop 关闭前 dispose 测试进程中的 application AsyncEngine；未修改生产 Scheduler 并发模型。
- 修正 recovery persistence Real API 对 `tick_once()` 全局 counters 的错误断言：Scheduler 会遍历所有当前可执行的 enabled scheduled triggers，因此测试改为以本测试 trigger 的 deterministic idempotency key / persistence rows 作为 per-trigger contract，不再假设 tenant 内只有一个 eligible trigger。

### 尚未完成的验收

- 本轮测试断言修复后的 `uv run pytest -q` 尚未由开发者重新执行。
- 本轮测试断言修复后的 Real API Gate 尚未由开发者重新执行。
- Runtime failure 的 scheduled persistence 尚未通过专项真实失败 Workflow 完成验收。

## 5. Migration 决策

当前 Phase 1.7-B 暂不新增 migration。现有 schema 已提供：

- `workflow_executions.idempotency_key`；
- tenant + idempotency unique constraint；
- Execution 状态机；
- input / output / error / started / ended 字段；
- audit / trace persistence。

只有当验收确认需要持久化 `next_run_at`、scheduler lease、misfire policy、per-trigger last-run state 或独立 scheduler state 时，才进入新的 migration 设计。

## 6. 测试状态

开发者最新反馈：

```text
Backend pytest:
245 passed, 17 deselected in 4.09s

Migration:
uv run alembic upgrade head -> success

Real API Gate:
16 passed, 1 failed
```

本轮失败已经从 AsyncEngine event loop 生命周期问题收敛为 recovery persistence Real API 的测试断言问题：`tick_once()` 按设计遍历所有 enabled scheduled triggers，因此 `counters["recovered"]` 是本次 tick 的全局 scheduler counter；当前环境中存在 3 个 eligible scheduled triggers，故得到 `recovered == 3`，而测试错误地将其解释为当前测试 trigger 的 per-trigger 数量。

该问题不属于 Scheduler 并发正确性或 persistence 实现缺陷，也不修改生产 `ScheduledTriggerScheduler`。测试现改为通过当前 trigger 的 recovery/current deterministic idempotency keys 查询 PostgreSQL `workflow_executions`，验证唯一 Execution、metadata 和重复 tick 不重复创建；global counter 仅验证至少存在 recovery dispatch。

另一次直接执行：

```text
uv run pytest -q tests/api_real/test_scheduled_trigger_api.py -m real_api
```

在未执行 Real API bootstrap、未注入 `TRIGGER_WORKFLOW_ID` 等上下文变量时得到 3 个 `TRIGGER_WORKFLOW_ID is required`，该结果属于测试入口使用方式不正确，不作为产品或测试 Gate 失败结论。应使用统一 Real API Gate 脚本准备上下文。

**当前不能标记 Backend / Real API Gate PASS；必须在本次测试断言修复后重新执行完整 Gate。**

## 7. Phase 1.7 下一阶段规划

```text
1.7-A Scheduled Trigger Backend Contract / Runtime / Recovery
      ↓ 已完成并通过基线审计
1.7-B Scheduler execution / persistence integration
      ↓ 当前
1.7-C Frontend Schedule Governance UI Contract
      ↓
1.7-D Real HTTP + Browser E2E scheduling contract
```

1.7-A / 1.7-B 均保持：

- 不引入 MQ / Event Bus / 独立 Worker；
- 不引入 Cron Engine / Temporal / Airflow；
- 不引入任意 Cron DSL；
- 不使用 JSON fixture 替代真实 PostgreSQL persistence。

## 8. 当前立即执行任务

**Phase 1.7-B：Scheduler execution / persistence integration**

固定顺序：

```text
基线审计
→ Persistence Contract 收口
→ Backend tests
→ Migration verification（仅需要时）
→ Real API
→ Runtime failure persistence 专项验收
→ 文档
→ main
```

本状态文件只记录已经确认的实际结果，不预先宣称未执行的 Gate 通过。
