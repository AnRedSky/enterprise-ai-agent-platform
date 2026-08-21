# 项目开发进度

> 本文只记录项目任务进度、实际验收结果、阻塞项和下一步任务。工程开发规则统一维护在 `docs/DEVELOPMENT.md`。

## 1. 当前主线

- 主分支：`main`
- 项目地址：`https://github.com/AnRedSky/enterprise-ai-agent-platform.git`
- 开发方式：所有功能直接在 `main` 开发与提交
- Phase 1.5：**已完成**
- Phase 1.6：**已完成并正式关闭**
- Phase 1.7：**已完成并正式关闭**
- 当前阶段：**Phase 1.8 待规划 / 下一阶段**
- 当前任务：**Phase 1.7 最终验收已完成**
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

## 4. Phase 1.7-C 完成收口

Phase 1.7-C 已按既有 Backend Contract 完成前端 Schedule Governance Integration，未新增 Backend API、migration 或 Scheduler runtime implementation。

### 已完成

- `WorkflowTrigger.trigger_type` 支持 `manual | scheduled`。
- 新增 `ScheduledTriggerConfig` 前端类型。
- Scheduled Trigger 默认配置 `timezone=UTC, interval_seconds=60`。
- 创建前校验 timezone 非空、interval_seconds 为正整数。
- Trigger inventory 展示 schedule contract。
- Scheduled Trigger 不显示 Manual Invoke。
- enable / disable / delete 沿用现有 Trigger API。
- Tenant 不由前端提交。
- 前端未实现 next-run、slot、recovery、lease、worker coordination。
- `WorkflowTriggers.test.ts` 覆盖 scheduled inventory / contract / create / invalid interval，以及 manual CRUD / invoke 回归。

### 测试结果

开发者已反馈本地 Frontend 测试全部通过。

Backend 最近实际 Gate 结果：

```text
uv run pytest -q
245 passed, 17 deselected

uv run alembic upgrade head
success

01_run_real_api_tests.ps1
17 passed
[PASS] Real API gate completed. Frontend/backend integration may proceed.
```

Frontend 回归结果：

```text
npm test
51 passed

npm run build
PASS

01_frontend_regression_gate.ps1
PASS
```

## 5. Phase 1.7-D Browser / Frontend-Backend E2E

Phase 1.7-D 复用既有 Browser E2E 测试基础设施，不新建重复 Gate。

### D-01 Browser Schedule Governance

- Browser 登录与真实 Workflow fixture；
- Schedule Governance 页面；
- Scheduled Trigger 创建；
- `timezone + interval_seconds` UI contract；
- Scheduled Trigger inventory；
- Scheduled Trigger 不显示 Manual Invoke。

### D-02 Trigger Lifecycle

- enable / disable / enable lifecycle；
- delete confirmation；
- delete 后 inventory 移除；
- 真实 HTTP API persistence 校验。

### D-03 Scheduler / Execution Boundary

通过真实 Browser → Vue → Backend HTTP → application scheduler → workflow execution 链路验证：

```text
Browser
  ↓
Vue Schedule Governance
  ↓
POST /workflows/{workflow_id}/triggers
  ↓
Scheduled Trigger persistence
  ↓
FastAPI application scheduler
  ↓
5 秒短 interval observation
  ↓
scheduled:{trigger_id}:{slot}
  ↓
workflow_executions
  ↓
Execution API observation
```

D-03 保持边界：

- 前端不计算 next-run；
- 前端不实现 scheduler polling；
- 不修改生产 Scheduler 语义以适配 E2E；
- 使用独立测试 Workflow / Trigger；
- 使用 5 秒短 interval 作为真实 scheduler observation 的受控测试数据。

### D-04 Regression Boundaries

D-04 验收确认：

- Browser Gate 独立执行；
- Browser Gate 不调用 Backend pytest；
- Browser Gate 不调用 Alembic migration；
- Browser Gate 不调用 Backend Real API Gate；
- Browser Gate 不调用 Frontend Vitest / build；
- Backend / Frontend / Browser 三层 Gate 保持独立；
- E2E 只验证真实浏览器、真实 Vue、真实 Backend HTTP 和 scheduler/execution observable contract；
- 未引入 Full Regression Gate 或跨目录测试编排。

### E2E 测试实现修正

已完成并保留以下稳定性修正：

1. Element Plus Scheduled 类型下拉采用键盘选择，避免 teleported dropdown 动画造成 locator.click 不稳定。
2. Config JSON 采用语义 JSON 断言，不要求 UI textarea 必须保持 minified 格式。
3. Trigger list 的真实 Backend API 返回数组；E2E persistence assertion 兼容真实数组响应，并保持对 `items` 包装响应的防御性读取。
4. Scheduler observation 使用 5 秒短 interval，避免使用 60 秒生产默认配置造成 Browser observation window 与真实 scheduler slot 不匹配。

相关提交：

```text
d84df68 fix(e2e): align trigger persistence assertion with API response contract
7236570 feat(e2e): cover scheduled trigger execution boundary
2039f028 fix: preserve scheduled slot recovery semantics
```

### Browser Gate 实际结果

开发者已反馈本轮 Frontend / Browser E2E 测试全部通过，D-03 Scheduler / Execution Boundary 因而完成实际验收；D-04 Regression Boundaries 随独立 Gate 规则完成收口。

Browser Gate 执行入口：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

结果：

```text
PASS
```

## 6. Phase 1.7 最终验收 / 关闭

Phase 1.7 最终验收确认以下闭环成立：

```text
Scheduled Trigger Governance
        ↓
Real Browser / Vue UI
        ↓
Real Backend HTTP Contract
        ↓
Persistent Scheduled Trigger
        ↓
Application Scheduler
        ↓
Deterministic Slot / Idempotency Key
        ↓
workflow_executions
        ↓
Execution Observable Contract
```

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

## 7. Phase 1.7 关闭后的下一步

Phase 1.7 不再继续追加 Schedule Governance / Scheduler / Execution E2E 范围。

下一阶段进入 Phase 1.8 规划，开始前必须重新：

1. 以远端 `main` 为基线同步代码；
2. 确认 Phase 1.8 领域范围与 Backend Contract；
3. 建立对应 Phase 计划文档；
4. 明确 Backend / Frontend / Browser 三层 Gate；
5. 按 `docs/DEVELOPMENT.md` 固定开发顺序推进。

当前不存在已确认的 Phase 1.7 阻塞项。
