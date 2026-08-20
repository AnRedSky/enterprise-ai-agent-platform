# Phase 1.6：Workflow Production Hardening / Trigger Contract

> 本计划由项目规范核查报告 `docs/14-project-compliance-audit-and-correction-plan.md` 形成，作为 Phase 1.5-G 完成后的阶段执行基线。工程规则以 `docs/DEVELOPMENT.md` 为唯一准则。

## 1. 阶段目标

建立 Workflow 从“内部执行 API”向“稳定业务入口”演进所需的 Trigger Contract，同时保持当前 FastAPI + PostgreSQL 单体边界，不提前引入 MQ、Worker、Cron 或具体分布式 Workflow Engine。

```text
Published Workflow
      ↓
Trigger Contract
      ↓
Tenant / RBAC / Lifecycle validation
      ↓
Idempotency / Concurrency governance
      ↓
Workflow Execution
      ↓
Audit / Trace
      ↓
Frontend Workflow Governance UI
```

## 2. 范围

本阶段实现：

1. Trigger domain contract。
2. Manual/API Trigger 与现有 Execution API 的边界统一。
3. Trigger identity / tenant scope。
4. Trigger enabled / disabled 生命周期约束。
5. Trigger 对 Published Workflow Version 的绑定规则。
6. Trigger request validation。
7. Trigger idempotency contract。
8. Trigger audit / trace 要求。
9. Trigger failure 与 execution failure 的错误码边界。
10. Backend Contract、Migration、pytest、Real API scenario。
11. Frontend API Type / Vitest / Workflow Governance UI。

本阶段暂不实现：

- MQ / Worker
- Cron Scheduler
- Event Bus
- 分布式任务队列
- Temporal / Airflow 等 Workflow Engine
- 高级 DAG 调度
- 自动补偿 / Saga
- 复杂 Policy DSL
- Workflow 可视化拖拽编辑器

## 3. Phase 1.6-A Trigger Contract

Backend Contract 已完成并正式关闭。接口：

```text
GET    /api/v1/workflows/{workflow_id}/triggers
POST   /api/v1/workflows/{workflow_id}/triggers
GET    /api/v1/workflows/{workflow_id}/triggers/{trigger_id}
PATCH  /api/v1/workflows/{workflow_id}/triggers/{trigger_id}
DELETE /api/v1/workflows/{workflow_id}/triggers/{trigger_id}
POST   /api/v1/workflows/{workflow_id}/triggers/{trigger_id}/invoke
```

第一轮字段：

- `name`
- `trigger_type`: 当前仅 `manual`
- `status`: `enabled` / `disabled`
- `config`
- Tenant / Workflow / creator 由认证上下文和服务层确定，不接受客户端 Tenant。

Backend 必须保证：

- Trigger 只能作用于当前 Tenant 可访问 Workflow。
- Trigger 只能调用 Published Workflow。
- Disabled / 非 Published Workflow 不得创建正常 Execution。
- Trigger invoke 必须复用现有 Execution State Machine。
- Trigger 必须复用 Idempotency / Concurrency / Reliability Governance。
- Audit / Trace 可关联 Workflow、Trigger、Execution。

Phase 1.6-A 已由开发者本地两道 Backend Gate 验收通过并正式关闭。

## 4. Phase 1.6-B Frontend Contract / Workflow Governance UI

Backend Contract 稳定后进入 Frontend。

### API Type

`frontend/src/api/workflows.ts` 新增：

- `WorkflowTrigger` TypeScript contract。
- `triggers()`
- `createTrigger()`
- `updateTrigger()`
- `deleteTrigger()`
- `invokeTrigger()`

Invoke 支持可选 `Idempotency-Key` header；Frontend 不提交 Tenant。

### UI

新增页面：

```text
/workflows/triggers
```

页面提供：

1. Workflow 选择。
2. Trigger 列表。
3. manual Trigger 创建。
4. enabled / disabled 状态展示。
5. Enable / Disable。
6. 删除。
7. Config JSON。
8. Invoke Input JSON。
9. Trigger Invoke。
10. 最近一次 Execution 摘要。

实现文件：

- `frontend/src/views/workflow-triggers/index.vue`
- `frontend/src/router/index.ts`

测试实现严格位于：

- `frontend/tests/api/workflows.test.ts`
- `frontend/tests/views/WorkflowTriggers.test.ts`

禁止在 `frontend/src/` 增加测试文件。

## 5. 固定实施顺序

```text
① Backend Trigger Domain + API Contract      ← 已完成
② Database Migration                          ← 已完成
③ Backend unit / integration / api_contract   ← 已完成
④ Backend Real API scenario                   ← 已完成
⑤ Frontend API Type + Vitest                  ← 已实现，待本地 Gate
⑥ Frontend UI                                 ← 已实现，待本地 Gate
⑦ Frontend production build                   ← 待执行
⑧ Backend Gate（独立）                        ← Phase 1.6-A 已通过
⑨ Frontend Gate（独立）                       ← 当前任务
⑩ 前后端联调
⑪ 文档更新
⑫ 直接提交 main
```

## 6. 验收门禁

### Backend

```powershell
cd backend
uv run pytest -q
uv run alembic upgrade head
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

### Frontend

```powershell
cd frontend
npm test
npm run build
```

或：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

两套 Gate 必须独立执行，任何一方不得调用另一方。

## 7. 当前状态

- Phase 1.5：已关闭。
- Phase 1.6-A Backend Contract：**已关闭**，两道 Backend Gate 已由开发者本地手工验收通过。
- Phase 1.6-B Frontend Contract / UI：**实现中，代码已提交 main，Frontend Gate 待开发者本地执行**。
- 当前不宣称 Frontend `npm test` / `npm run build` 已通过，因为本轮尚未实际执行。
- Frontend Gate 通过后，进入 Trigger UI 与 Backend Real API 的实际联调；如需要 Browser / Frontend-Backend E2E，必须作为第三独立测试层设计。

责任角色：开发执行。
