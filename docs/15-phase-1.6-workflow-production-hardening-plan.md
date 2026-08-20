# Phase 1.6：Workflow Production Hardening / Trigger Contract

> 本计划由项目规范核查报告 `docs/14-project-compliance-audit-and-correction-plan.md` 形成，作为 Phase 1.5-G 完成后的下一阶段正式执行基线。
>
> 本阶段不回头重复 Circuit Breaker；重点是在已有 Workflow Definition / Publish / Execution / Reliability / Governance 基础上建立稳定、可审计、可幂等的 Workflow Trigger Contract。工程规则以 `docs/DEVELOPMENT.md` 为唯一准则。

## 1. 阶段目标

建立 Workflow 从“内部执行 API”向“稳定业务入口”演进所需的 Trigger Contract，同时保持当前 FastAPI + PostgreSQL 单体边界，不提前引入 MQ、Worker、Cron 或具体分布式 Workflow Engine。

目标链路：

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
```

## 2. 范围

### 本阶段实现

1. Trigger domain contract。
2. Manual/API Trigger 与现有 Execution API 的边界统一。
3. Trigger identity / tenant scope。
4. Trigger enabled / disabled 生命周期约束。
5. Trigger 对 Published Workflow Version 的绑定规则。
6. Trigger request validation。
7. Trigger idempotency contract，禁止同一业务请求重复创建 Execution。
8. Trigger audit / trace 要求。
9. Trigger failure 与 execution failure 的错误码边界。
10. Backend Contract、Migration（如需要）、pytest、Real API scenario。
11. Frontend API Type / Vitest / UI（仅在 Backend Contract 稳定后进入）。

### 本阶段暂不实现

- MQ / Worker。
- Cron Scheduler。
- Event Bus。
- 分布式任务队列。
- Temporal / Airflow 等 Workflow Engine。
- 高级 DAG 调度。
- 自动补偿 / Saga。
- 复杂 Policy DSL。
- Workflow 可视化拖拽编辑器。

## 3. 第一项任务：Phase 1.6-A Trigger Contract

### Backend Contract

候选接口：

```text
GET    /api/v1/workflows/{workflow_id}/triggers
POST   /api/v1/workflows/{workflow_id}/triggers
GET    /api/v1/workflows/{workflow_id}/triggers/{trigger_id}
PATCH  /api/v1/workflows/{workflow_id}/triggers/{trigger_id}
DELETE /api/v1/workflows/{workflow_id}/triggers/{trigger_id}
POST   /api/v1/workflows/{workflow_id}/triggers/{trigger_id}/invoke
```

> 具体字段、状态码和数据库结构必须在 Backend Contract 实施时以当前代码模型和现有 API 约束为准，本表不提前固化未验证字段。

### 必须保证

- Trigger 不允许客户端指定任意 Tenant。
- Trigger 只能作用于当前 Tenant 可访问的 Workflow。
- Trigger 默认只能指向 Published Version；若未来支持显式 version，必须经过 Governance 校验。
- Disabled / 非 Published Workflow 不得通过 Trigger 创建正常 Execution。
- Trigger invoke 必须进入现有 Execution State Machine，而不是复制 Runtime 执行逻辑。
- Trigger 必须复用现有 Idempotency / Concurrency / Reliability Governance。
- Trigger invoke 的 Audit / Trace 必须能关联 Workflow、Trigger、Execution。

## 4. 固定实施顺序

```text
① Backend Trigger Domain + API Contract
② Database Migration（如需要）
③ Backend unit / integration / api_contract tests
④ Backend Real API fixture / scenario
⑤ Frontend API Type + Vitest
⑥ Frontend UI
⑦ Frontend production build
⑧ Backend Gate（独立）
⑨ Frontend Gate（独立）
⑩ 前后端联调
⑪ 文档更新
⑫ 直接提交 main
```

## 5. 验收门禁

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

两套 Gate 必须独立执行，任何一方不得调用另一方。

## 6. 追踪要求

每项实现必须同步更新：

- `docs/PROJECT_STATUS.md`
- 本 Phase 文档
- 如发生工程错误：`docs/error-tracking/`

所有测试结果必须来自实际执行，不得预填。

## 7. 当前状态

- Phase 1.6：已建立执行基线，尚未开始代码实现。
- Phase 1.6-A：Trigger Contract，**下一项执行任务**。
- 责任角色：开发执行。
- 开始条件：以远端 `main` 最新提交为基线。
- 完成条件：Backend Contract → Backend 验收 → Frontend 独立验收 → Real API → 独立 Regression Gate → 文档 → main。
