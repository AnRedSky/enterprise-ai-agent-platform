# Phase 1.8 计划：Event / Webhook Trigger Expansion

> 状态：**正式关闭（1.8-A ～ 1.8-F 全部完成）**
>
> 本文维护 Phase 1.8 的领域范围、架构、Contract、任务拆解、验收门禁和最终状态。实际验收结果详见 `docs/PHASE_1_8_ACCEPTANCE.md` 与 `docs/PROJECT_STATUS.md`。

## 1. Phase 1.8 目标

Phase 1.7 已完成 Scheduled Trigger 从 Governance UI 到 Scheduler / Execution 的真实闭环。Phase 1.8 将 Trigger 入口从“时间驱动”扩展到“外部事件驱动”，形成可治理、可审计、可幂等的 Webhook / Event Trigger 能力。

目标闭环：

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

## 2. 范围

### In Scope

1. Webhook Trigger Domain Contract。
2. Webhook Trigger 创建、查询、更新、启用、禁用、删除。
3. 外部事件入口 API。
4. 请求身份校验与基础安全边界。
5. Event Idempotency Contract，保证重复投递不产生重复 Execution。
6. Trigger → Workflow Execution 的 Backend Real API Contract。
7. Trace / Audit 对事件入口和 Execution 的关联。
8. Frontend Trigger Governance 中 Webhook Trigger 的配置与 inventory 展示。
9. Browser E2E：真实 Browser → Vue → Backend HTTP → Webhook → Execution observable contract。

### Out of Scope

- 不重写现有 Scheduled Scheduler。
- 不引入 MQ/Kafka 等消息基础设施。
- 不实现通用 Event Bus。
- 不实现任意第三方 OAuth 平台。
- 不允许 Webhook 直接执行 Python/任意代码。
- 不在本阶段引入多 Agent 协作。
- 不把 Webhook 请求处理改造成跨服务分布式任务系统。

## 3. Domain / Architecture

继续遵循现有分层：

```text
API
 ↓
Trigger Service
 ↓
Workflow Execution Service
 ↓
Runtime
 ↓
Repository
 ↓
PostgreSQL / Redis
```

Webhook 入口与 Scheduled Trigger 共用 Trigger Domain 与 Workflow Execution Contract，但调度机制保持独立：

```text
Scheduled Trigger                 Webhook Trigger
       │                                  │
       ▼                                  ▼
Application Scheduler             HTTP Event Endpoint
       │                                  │
       └────────── Trigger Service ───────┘
                         │
                         ▼
                Idempotent Execution Claim
                         │
                         ▼
                 Workflow Execution
```

## 4. Backend Contract

### 4.1 Trigger configuration

创建 / 更新请求支持：

```json
{
  "trigger_type": "webhook",
  "config": {
    "auth_mode": "secret",
    "secret": "<write-only secret, 16-256 chars>",
    "event_id_field": "event_id"
  }
}
```

持久化后的内部 config 为：

```json
{
  "auth_mode": "secret",
  "secret_hash": "<sha256>",
  "event_id_field": "event_id"
}
```

`secret` 只允许写入，不从 Trigger API response 返回；`secret_hash` 也不从 response 返回。

### 4.2 Webhook endpoint

```text
POST /api/v1/webhooks/{trigger_id}
```

Headers：

```text
X-Webhook-Secret: <secret>
Idempotency-Key: <optional event identity>
X-Request-ID: <optional request correlation id>
```

如果没有 `Idempotency-Key`，Backend 从 `event_id_field` 指定的顶层 payload 字段提取事件身份；两者都不存在时返回 `422`。

响应：

```json
{
  "status": "accepted | duplicate",
  "request_id": "...",
  "execution_id": "...",
  "idempotency_key": "webhook:{trigger_id}:{event_identity}"
}
```

首次成功 claim 返回 `202 accepted`；重复投递返回 `200 duplicate`。认证失败返回 `401`，禁用 Trigger 返回 `409`。

### 4.3 Idempotency

优先使用：

```text
webhook:{trigger_id}:{event_identity}
```

当该形式超出 `workflow_executions.idempotency_key` 的 100 字符边界时：

```text
webhook:{sha256(trigger_id + ':' + event_identity)}
```

因此公开响应的 durable key 始终不超过 100 字符，并满足：

```text
first delivery
    → one durable Execution

repeated delivery
    → no second Execution
```

最终收敛依赖现有 `workflow_executions` 的 `(tenant_id, idempotency_key)` 唯一约束，不依赖内存锁。

## 5. Database / Migration

### 1.8-B 审计结论：**无需新增 Migration**

现有 `workflow_triggers` 已具备 `trigger_type + config + tenant/workflow/status` 表达能力，既有 `0022_workflow_trigger` migration 无需修改。

现有 `workflow_executions` 已具备 `(tenant_id, idempotency_key)` 唯一持久化边界，因此本阶段不新增 `webhook_events` 表，也不新增数据库字段。

## 6. Frontend Contract

Frontend 增加：

- Webhook Trigger 类型展示；
- Webhook 配置表单；
- enabled / disabled lifecycle；
- Webhook endpoint 展示；
- inventory；
- 不显示 Scheduled Trigger 专属字段。

Frontend 不负责：

- 生成最终 durable event identity；
- 判断是否 duplicate；
- 直接创建 Workflow Execution；
- 实现 Webhook authentication。

## 7. Browser E2E Contract

```text
Browser
  ↓
Vue Trigger Governance
  ↓
Create Webhook Trigger
  ↓
真实 Backend HTTP
  ↓
Webhook Endpoint
  ↓
Workflow Execution
  ↓
Execution API observation
```

覆盖：

1. Webhook Trigger 创建。
2. Inventory 展示。
3. Enable / Disable。
4. 合法 Webhook 请求产生 Execution。
5. 重复 Event 不产生第二个 Execution。
6. 无效 secret 被拒绝。
7. 删除后 endpoint 不再可用。
8. Browser Gate 与 Backend / Frontend Gate 保持独立。

## 8. 任务拆解与最终状态

### 1.8-A 需求 / Contract Baseline

**已完成**

- [x] 明确 Phase 1.8 范围。
- [x] 明确 Webhook / Event Trigger 与 Scheduled Trigger 的边界。
- [x] 明确 API / Idempotency / Security 原则。
- [x] 明确三层测试 Gate。

### 1.8-B Backend Domain + API

**已完成**

- [x] 审计现有 Trigger Model / Schema / Service。
- [x] 确认无需 Migration。
- [x] 实现 Webhook Trigger config contract。
- [x] 实现 Webhook endpoint。
- [x] 实现 authentication / validation。
- [x] 实现 durable idempotent execution claim。
- [x] 添加 Webhook config unit / integration / API Contract / Real API tests。
- [x] 本地 Backend Gate 通过。

### 1.8-C Frontend API + Governance UI

**已完成**

- [x] 更新 API types。
- [x] 更新 Trigger inventory。
- [x] 增加 Webhook 创建 / 编辑 UI。
- [x] 增加 lifecycle 操作。
- [x] 添加 Vitest。
- [x] `npm run build` 通过。
- [x] Frontend Regression Gate 通过。

### 1.8-D Real API / Runtime Boundary

**已完成**

- [x] accepted / duplicate / authentication / lifecycle Contract。
- [x] Execution persistence。
- [x] duplicate event convergence。
- [x] authentication failure。
- [x] 删除 / disable 后 endpoint 行为。
- [x] 缺失 event identity `422` Contract。
- [x] bounded durable idempotency key Contract。
- [x] Backend default regression 通过。
- [x] Real API Gate 通过。

### 1.8-E Browser E2E

**已完成**

- [x] Browser 创建 Webhook Trigger。
- [x] Browser inventory / lifecycle。
- [x] Browser 发起真实 Webhook request。
- [x] Browser 观察 Execution。
- [x] Browser 验证 duplicate / rejected / lifecycle security contract。

### 1.8-F Final Acceptance

**已完成并正式关闭**

- [x] Backend Gate。
- [x] Frontend Gate。
- [x] Browser E2E Gate。
- [x] PROJECT_STATUS 更新。
- [x] Phase 1.8 验收文档收口。
- [x] 工程清理规则复核。

## 9. 本地验收门禁与实际结果

### Backend

```powershell
cd backend
uv run pytest -q
uv run alembic upgrade head
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

本阶段开发者实际反馈：

```text
uv run pytest -q
→ 257 passed, 20 deselected in 4.95s

Real API Gate
→ 20 passed in 37.94s
→ [PASS] Real API gate completed.
```

Phase 1.8-B 已实际执行 `uv run alembic upgrade head` 并通过；本阶段无新增 Migration。

### Frontend

```powershell
cd frontend
npm test
npm run build
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

本阶段开发者实际反馈：

```text
Vitest → 13 test files passed, 52 tests passed
Production build → succeeded, 1709 modules transformed
Frontend Regression Gate → [PASS]
```

### Browser

```powershell
cd frontend
npx playwright test --list --project="Desktop Chrome"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

本阶段开发者实际反馈：

```text
3 tests listed
3 passed
[PASS] Phase 1.7-D browser E2E gate completed.
```

## 10. 开发与工程治理

1. 所有开发工作以最新 `main` 为唯一基线。
2. 禁止创建开发分支、临时分支或任务分支；直接在 `main` 推进。
3. 禁止提交、触发、依赖 GitHub Actions workflow run；所有测试由开发者本地执行。
4. 本地测试结果只有在开发者实际反馈后才能写入状态文档。
5. 不提交 secret、Real API context、Playwright trace/screenshot 等本地运行产物。
6. 不修改 Phase 1.7 Scheduled Scheduler 以适配 Webhook。
7. 不引入 MQ/Kafka、通用 Event Bus 或新的 Webhook 持久化表。
8. Durable key 必须满足 `workflow_executions.idempotency_key` 的 100 字符 schema 边界。

## 11. 最终结论

**Phase 1.8 Event / Webhook Trigger Expansion 正式关闭。**

1.8-A ～ 1.8-F 全部完成，Backend / Frontend / Browser 三层本地 Gate 均已通过。下一阶段必须从最新 `main` 基线开始，先完成需求 / 架构确认与任务拆解，再进入实现。
