# Phase 1.7-D：Browser / Frontend-Backend E2E Scheduling Contract

## 1. 目标

在 Phase 1.7-A/B 已完成 Scheduled Trigger Backend / Scheduler / persistence 基线、Phase 1.7-C 已完成 Schedule Governance Frontend Integration 的基础上，建立真实 Browser / Frontend-Backend E2E 链路。

本阶段验证真实用户路径，而不是重新实现 Scheduler：

```text
Browser
  ↓
Frontend Schedule Governance UI
  ↓
real HTTP API
  ↓
Trigger persistence
  ↓
application scheduler
  ↓
WorkflowExecutionService
  ↓
workflow_executions
  ↓
Frontend execution / trigger state
```

## 2. 基线与边界

Phase 1.7-C 已确认前端只消费既有 Trigger HTTP Contract：

```text
GET/POST/PATCH/DELETE /workflows/{workflow_id}/triggers
POST /workflows/{workflow_id}/triggers/{trigger_id}/invoke
```

Scheduled Trigger 配置严格使用：

```json
{
  "timezone": "UTC",
  "interval_seconds": 60
}
```

Frontend 不实现：

- scheduler polling
- interval slot
- idempotency key
- recovery slot
- advisory lock
- worker coordination
- next_run_at

Phase 1.7-D 只验证这些后端能力通过真实系统边界产生预期结果。

## 3. D-01 Browser Schedule Governance

使用 Desktop Chrome 验证：

1. 进入 Workflow Trigger Governance。
2. 选择目标 Workflow。
3. 创建 Scheduled Trigger。
4. 验证 UI 使用 `timezone + interval_seconds` Contract。
5. 验证创建成功后 Trigger 出现在列表。
6. 验证 Scheduled Trigger 不显示 Manual Invoke。

## 4. D-02 Trigger Lifecycle

通过真实 HTTP Backend 验证 Browser 操作产生的持久化结果：

1. Scheduled Trigger create -> 201。
2. Trigger list -> 返回创建的 scheduled Trigger。
3. Disable -> persisted status 更新。
4. Enable -> persisted status 恢复。
5. Delete -> persisted Trigger 删除。

前端不直接访问数据库；验证应通过真实 HTTP API 或已有受控测试上下文完成。

## 5. D-03 Scheduler / Execution Boundary

E2E 应覆盖至少一个可控 scheduled interval，并验证：

- application scheduler 能消费已持久化 Trigger；
- scheduler 产生的 execution 使用已有 deterministic idempotency contract；
- execution 最终进入已有 workflow execution persistence boundary；
- Browser / API 能观察到对应 Execution；
- 不依赖前端计算 next-run 或 scheduler state。

测试必须使用独立测试数据，并避免与后台 scheduler 产生 slot 竞争。优先使用专用测试 Workflow / Trigger 和可控短 interval；不得通过修改生产 Scheduler 语义来适配 E2E。

## 6. D-04 Regression Boundaries

Phase 1.7-D 不复制已有 Gate：

- Backend pytest 不在 E2E wrapper 中重复执行；
- migration 不在 E2E wrapper 中重复执行；
- Backend Real API 全量 Gate 不在 E2E wrapper 中重复执行；
- Frontend Vitest / production build 不在 E2E wrapper 中重复执行。

E2E 只验证 Browser + real HTTP + application runtime 的跨层契约。

## 7. E2E 测试入口

统一入口继续位于：

```text
frontend/scripts/test/e2e/
```

推荐命令：

```powershell
cd frontend
npx playwright test --list --project="Desktop Chrome"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

如果 E2E 依赖的测试上下文需要环境变量，应由 E2E bootstrap 统一准备，不在测试代码中硬编码租户、Workflow 或数据库 ID。

## 8. 非目标

本阶段不做：

- 新 Scheduler API；
- 新 persistence model；
- Cron DSL；
- MQ / Event Bus；
- 独立 Worker；
- Scheduler metrics dashboard；
- next-run persistence；
- Frontend scheduler state implementation。

## 9. 完成定义

Phase 1.7-D 完成条件：

1. Desktop Chrome Browser E2E 能创建 Scheduled Trigger。
2. Browser E2E 能验证 Trigger lifecycle。
3. Real HTTP 能确认 Trigger persistence contract。
4. Scheduler 能在真实应用运行时产生 Execution。
5. Execution 能通过已有 persistence / API boundary 被观察。
6. E2E 不复制其他测试 Gate。
7. E2E 测试入口、环境准备和清理职责明确。
8. PROJECT_STATUS 记录实际结果。
9. 完成后再评估 Phase 1.7 最终关闭。
