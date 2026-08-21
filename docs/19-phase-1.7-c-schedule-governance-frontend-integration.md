# Phase 1.7-C：Schedule Governance / Frontend Integration

## 1. 目标

在 Phase 1.7-A/B 已存在的 Scheduled Trigger Backend Contract、Scheduler Runtime 和 `workflow_executions` persistence boundary 之上，完成前端 Schedule Governance UI，不重新实现后端 Scheduler。

本阶段只消费既有 HTTP Contract：

```text
GET/POST/PATCH/DELETE /workflows/{workflow_id}/triggers
POST /workflows/{workflow_id}/triggers/{trigger_id}/invoke
```

Scheduled Trigger 初始配置继续严格使用：

```json
{
  "timezone": "UTC",
  "interval_seconds": 60
}
```

Frontend 不自行计算 Scheduler next-run、slot、recovery、lease 或 worker 状态；这些属于后端运行时职责。

## 2. 基线审计结论

当前 main 已存在 Workflow Trigger Governance 页面、Workflow Trigger API client、Trigger CRUD、enable/disable 和 manual invoke。现有前端类型把 `trigger_type` 限定为 `manual`，因此无法消费已存在的 `scheduled` Backend Contract。

后端已经提供统一 Trigger response，其中包含 `trigger_type`、`status`、`config`、`workflow_id`、`tenant_id` 等字段；Tenant 仍由后端鉴权上下文决定，前端不提交 tenant_id。

因此本阶段不新增 Backend API，不新增 migration，不复制 Trigger Service，不增加 Scheduler state API。

## 3. 实施范围

### C-01 API Type Contract

- 扩展 `WorkflowTrigger.trigger_type`：`manual | scheduled`。
- 增加 `ScheduledTriggerConfig` 前端类型。
- `createTrigger` 支持两种既有 Trigger 类型。
- 保持 Tenant 字段只读，不允许前端创建/修改 tenant。

### C-02 Schedule Governance UI

- Trigger 创建表单支持 `manual / scheduled`。
- Scheduled 类型默认生成 `timezone + interval_seconds` 配置。
- 创建前做最小 UI 校验：timezone 非空、interval_seconds 为正整数。
- Trigger 列表展示 Schedule 配置。
- scheduled Trigger 不显示 manual Invoke 操作。
- enable/disable/delete 沿用现有 Backend Contract。

### C-03 Runtime Boundary

前端只展示 Backend 已返回的 Execution；不在前端实现：

- scheduler polling
- interval slot
- idempotency key generation for scheduled execution
- recovery slot
- advisory lock
- worker coordination
- next_run_at

Manual invoke 仍然通过现有 `/invoke` API 验证真实 Workflow Execution。

### C-04 Frontend Tests

`frontend/tests/views/WorkflowTriggers.test.ts` 覆盖：

- scheduled Trigger inventory
- schedule contract 展示
- scheduled Trigger 创建
- invalid interval 拦截
- manual Trigger CRUD
- manual Trigger invoke

## 4. 非目标

本阶段不做：

- Cron DSL
- MQ / Event Bus
- 独立 Worker
- Temporal / Airflow
- Scheduler lease UI
- scheduler metrics dashboard
- next-run persistence
- per-trigger last-run persistence
- 新数据库 migration
- 新 Backend scheduler API

## 5. 验收 Gate

### Frontend Regression

```powershell
cd frontend
npm test
npm run build
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

### Backend Regression / Real API

Frontend Contract 变更不替代 Backend Gate；后端仍按独立 Gate 执行：

```powershell
cd backend
uv run pytest -q
uv run alembic upgrade head
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

### Browser E2E

Phase 1.7-D 再将 Schedule 创建、启停与真实 Runtime/Execution 链路纳入 Browser / Frontend-Backend E2E，不在 C 阶段复制 E2E Gate。

## 6. 清理原则

删除已被正式 Release Gate 替代、且没有引用的旧 Backend regression wrapper；保留 `backend/scripts/test/release` 作为唯一 Backend Release Gate，保留 Real API 唯一入口。

不删除仍有明确职责的 `dev / evaluation / migration / api-real / integration / phase / release` 目录。

## 7. 完成定义

Phase 1.7-C 完成条件：

1. Frontend API 类型支持 scheduled Trigger。
2. Schedule Governance UI 能创建、展示、启停、删除 scheduled Trigger。
3. Frontend 不自行实现 scheduler runtime state。
4. Vitest 覆盖 Schedule Contract。
5. Frontend production build 通过。
6. Backend Real API Gate 保持通过。
7. PROJECT_STATUS 与本阶段文档记录实际测试结果。
8. 变更直接提交 main。
