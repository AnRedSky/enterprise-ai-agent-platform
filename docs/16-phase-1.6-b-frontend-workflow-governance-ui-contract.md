# Phase 1.6-B：Frontend Contract / Workflow Governance UI Contract

> Phase 1.6-A Backend Contract 已由开发者本地两道 Gate 验收通过后关闭。本阶段严格依据 `docs/DEVELOPMENT.md` 的固定顺序，在稳定 Backend Contract 基础上推进 Frontend API Types、Vitest 与 Workflow Trigger Governance UI。

## 1. 阶段目标

把 Phase 1.6-A 已稳定的 Workflow Trigger Backend Contract 映射到 Vue 3 前端，形成可测试、可操作、可审计边界清晰的 Workflow Governance UI。

```text
Backend Trigger Contract
        ↓
Frontend API Types
        ↓
Vitest Contract Tests
        ↓
Trigger Governance UI
        ↓
Frontend production build
        ↓
后续 Real API / 联调
```

## 2. Backend Contract 依赖

Frontend 不重新定义业务字段，严格使用 Backend Contract：

```text
GET    /api/v1/workflows/{workflow_id}/triggers
POST   /api/v1/workflows/{workflow_id}/triggers
GET    /api/v1/workflows/{workflow_id}/triggers/{trigger_id}
PATCH  /api/v1/workflows/{workflow_id}/triggers/{trigger_id}
DELETE /api/v1/workflows/{workflow_id}/triggers/{trigger_id}
POST   /api/v1/workflows/{workflow_id}/triggers/{trigger_id}/invoke
```

Trigger 字段：

- `id`
- `tenant_id`
- `workflow_id`
- `name`
- `trigger_type`：当前仅 `manual`
- `status`：`enabled` / `disabled`
- `config`
- `created_by`
- `created_at`
- `updated_at`

Invoke：

```json
{
  "input_data": {}
}
```

可选 HTTP Header：

```text
Idempotency-Key: <business-request-key>
```

Frontend 不提交 `tenant_id`，Tenant scope 由认证上下文和 Backend Service 决定。

## 3. UI Contract

### Workflow Trigger Governance 页面

页面提供：

1. 当前可访问 Workflow 选择。
2. Trigger 列表。
3. 创建 manual Trigger。
4. 查看 enabled / disabled 状态。
5. Enable / Disable。
6. 删除 Trigger。
7. JSON Config 输入。
8. Invoke Input JSON 输入。
9. Invoke Trigger。
10. 显示最近一次 Trigger Execution 的 ID、状态和 Published Version。

页面入口：

```text
/workflows/triggers
```

### Governance 约束

- 未选择 Workflow 时禁止 Trigger 操作。
- Disabled Trigger 不允许从 UI 发起 Invoke。
- Invoke 使用前端生成的请求幂等键，避免重复点击造成业务请求重复创建 Execution。
- UI 不绕过 Trigger API 直接调用 Execution Runtime。
- UI 不自行实现 Tenant / Published Version / Retry / Circuit Breaker 等 Backend Governance 规则。
- Backend 返回的业务失败由 UI 明确提示，不通过前端静默降级改变业务语义。

## 4. 实现范围

已实现：

- `frontend/src/api/workflows.ts`
  - `WorkflowTrigger` TypeScript contract。
  - Trigger list/create/update/delete/invoke API。
  - Invoke Idempotency-Key header。
- `frontend/src/views/workflow-triggers/index.vue`
  - Trigger Governance UI。
  - Workflow 选择、Trigger CRUD、状态治理、Invoke、Execution 摘要。
- `frontend/src/router/index.ts`
  - `/workflows/triggers` 路由。
- `frontend/tests/api/workflows.test.ts`
  - Trigger API Type / request contract tests。
- `frontend/tests/views/WorkflowTriggers.test.ts`
  - Trigger Governance UI 行为测试。

严格保持：

```text
frontend/src/       # 业务源码
frontend/tests/     # 测试实现
frontend/scripts/test/  # Frontend Gate
```

未创建任何 `frontend/src/*.test.*`。

## 5. 测试门禁

Frontend 独立执行：

```powershell
cd frontend
npm test
npm run build
```

Frontend Regression Gate：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

本阶段不调用：

- `uv run pytest`
- Alembic
- Backend Real API Gate
- Backend Regression Gate

Backend 与 Frontend 继续保持完全独立。

## 6. 当前验收状态

代码已提交 `main`，但本次实现尚未在开发者本地执行 `npm test` / `npm run build`，因此不得标记 Frontend Gate 已通过。

下一步固定动作：

1. 开发者本地 `cd frontend`。
2. 执行 `npm test`。
3. 执行 `npm run build`。
4. 若失败，只修复 Frontend Contract / UI，不调用 Backend Gate 替代验证。
5. Frontend Gate 通过后进入 Frontend / Backend 实际联调与 Trigger Real API UI 验收。

## 7. 责任与风险

- 责任角色：开发执行。
- 当前状态：Frontend Contract / UI 实现完成，Frontend Gate 待本地执行。
- 主要风险：Element Plus 组件测试 Stub 与 TypeScript/Vite production build 兼容性需由本地环境确认。
- 不引入 MQ / Worker / Cron / Event Bus / Temporal。
