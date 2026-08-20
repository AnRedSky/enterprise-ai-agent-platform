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

已落地第一轮候选接口：

```text
GET    /api/v1/workflows/{workflow_id}/triggers
POST   /api/v1/workflows/{workflow_id}/triggers
GET    /api/v1/workflows/{workflow_id}/triggers/{trigger_id}
PATCH  /api/v1/workflows/{workflow_id}/triggers/{trigger_id}
DELETE /api/v1/workflows/{workflow_id}/triggers/{trigger_id}
POST   /api/v1/workflows/{workflow_id}/triggers/{trigger_id}/invoke
```

当前第一轮实现字段：

- `name`
- `trigger_type`：当前仅 `manual`
- `status`：`enabled` / `disabled`
- `config`
- Tenant / Workflow / creator 由认证上下文和服务层确定，不接受客户端 Tenant。

### 必须保证

- Trigger 不允许客户端指定任意 Tenant。
- Trigger 只能作用于当前 Tenant 可访问的 Workflow。
- Trigger 默认只能指向 Published Version；当前通过 `Workflow.published_version_id` 在 invoke 时解析并校验 Published Version。
- Disabled / 非 Published Workflow 不得通过 Trigger 创建正常 Execution。
- Trigger invoke 必须进入现有 Execution State Machine，而不是复制 Runtime 执行逻辑。
- Trigger 必须复用现有 Idempotency / Concurrency / Reliability Governance。
- Trigger invoke 的 Audit / Trace 必须能关联 Workflow、Trigger、Execution。

### 当前 Backend 实现

- `backend/app/models/workflow_trigger.py`
- `backend/app/services/workflow_trigger.py`
- `backend/app/api/workflows.py`
- `backend/alembic/versions/0022_workflow_trigger.py`
- `backend/tests/unit/test_workflow_trigger.py`
- `backend/tests/api_contract/test_api_workflows_endpoints.py`
- `backend/alembic/env.py` 已注册 Trigger model。

当前代码已提交 `main`，但**尚未宣称 Backend Gate / Real API 已通过**；验收结果必须以实际执行记录为准。

## 4. 固定实施顺序

```text
① Backend Trigger Domain + API Contract      ← 当前已实现第一轮
② Database Migration（如需要）              ← 已创建 0022
③ Backend unit / integration / api_contract tests ← 已补充，待实际 Gate
④ Backend Real API fixture / scenario        ← 下一步
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

- Phase 1.6：已建立执行基线。
- Phase 1.6-A：**Backend Contract 实现中**。
- Backend Trigger domain / API / migration / contract tests 第一轮已提交 `main`。
- Backend pytest、migration/head、Real API 尚未完成本轮最终验收。
- Frontend 尚未开始；必须等待 Backend Contract 稳定并通过 Backend Gate 后进入。
- 责任角色：开发执行。
- 完成条件：Backend Contract → Backend 验收 → Frontend 独立验收 → Real API → 独立 Regression Gate → 文档 → main。
