# Phase 1.8 计划：Event / Webhook Trigger Expansion

> 状态：**1.8-B Backend Domain + API 实现中**
>
> 本文只维护 Phase 1.8 的领域范围、架构、任务拆解、Contract、验收门禁和实施顺序。实际进度与测试结果同步记录在 `docs/PROJECT_STATUS.md`。

## 1. Phase 1.8 目标

Phase 1.7 已完成 Scheduled Trigger 从 Governance UI 到 Scheduler / Execution 的真实闭环。Phase 1.8 不重复建设 scheduler，而是把 Trigger 入口从“时间驱动”扩展到“外部事件驱动”，形成可治理、可审计、可幂等的 Webhook / Event Trigger 能力。

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
8. Frontend Schedule/Trigger Governance 中 Webhook Trigger 的配置与 inventory 展示。
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

Webhook 入口与 Scheduled Trigger 共用 Trigger Domain 与 Workflow Execution Contract，但两者的调度机制保持独立：

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

请求体作为 workflow `input_data` 的事件载荷来源。

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

事件入口支持显式事件 ID 或标准 `Idempotency-Key`。

最终 durable key：

```text
webhook:{trigger_id}:{event_identity}
```

同一 Tenant + Trigger + Event Identity 在重复投递下必须满足：

```text
first delivery
    → one durable Execution

repeated delivery
    → no second Execution
```

最终收敛依赖现有 `workflow_executions` 的 `(tenant_id, idempotency_key)` 唯一约束，不依赖内存锁。

### 4.4 Security boundary

```text
Request
 ↓
Trigger enabled?
 ↓
Authentication / secret validation
 ↓
Payload / event identity validation
 ↓
Durable Idempotency Claim
 ↓
Execution
```

Webhook secret 仅保存 SHA-256 hash；secret/token 不进入 AuditLog、Trace metadata 或普通业务日志。

## 5. Database / Migration

### 1.8-B 审计结论：**无需新增 Migration**

现有 `workflow_triggers` 已具备 `trigger_type + config + tenant/workflow/status` 表达能力，既有 `0022_workflow_trigger` migration 无需修改。

现有 `workflow_executions` 已具备 `(tenant_id, idempotency_key)` 唯一持久化边界，可以直接表达 Webhook event durable claim，因此本阶段不新增 `webhook_events` 表。

本次实现只扩展既有 Trigger config contract，并新增 HTTP / Service 层，不新增数据库表或字段。

## 6. Frontend Contract

Frontend 增加：

- Webhook Trigger 类型展示；
- Webhook 配置表单；
- enabled / disabled lifecycle；
- Webhook endpoint 展示；
- inventory；
- 不显示 Scheduled Trigger 专属字段；
- 不计算事件状态、Execution idempotency 或 runtime。

Frontend 不负责：

- 生成最终 durable event identity；
- 判断是否 duplicate；
- 直接创建 Workflow Execution；
- 实现 Webhook authentication。

## 7. Browser E2E Contract

新增独立 Browser 测试链路：

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

至少覆盖：

1. Webhook Trigger 创建。
2. Inventory 展示。
3. Enable / Disable。
4. 合法 Webhook 请求产生 Execution。
5. 重复 Event 不产生第二个 Execution。
6. 无效 secret 被拒绝。
7. 删除后 endpoint 不再可用。
8. Browser Gate 与 Backend / Frontend Gate 保持独立。

## 8. 任务拆解

### 1.8-A 需求 / Contract Baseline

状态：**完成**

- [x] 明确 Phase 1.8 范围。
- [x] 明确 Webhook / Event Trigger 与 Scheduled Trigger 的边界。
- [x] 明确 API / Idempotency / Security 原则。
- [x] 明确三层测试 Gate。

### 1.8-B Backend Domain + API

状态：**实现中，本批核心 Contract 已落地**

- [x] 审计现有 Trigger Model / Schema / Service。
- [x] 确认无需 Migration。
- [x] 实现 Webhook Trigger config contract。
- [x] 实现 Webhook endpoint。
- [x] 实现 authentication / validation。
- [x] 实现 durable idempotent execution claim。
- [x] 添加 Webhook config unit tests。
- [ ] 补齐 integration / api_contract / api_real tests。
- [ ] 执行本地 Backend Gate。

### 1.8-C Frontend API + Governance UI

状态：待开发

- [ ] 更新 API types。
- [ ] 更新 Trigger inventory。
- [ ] 增加 Webhook 创建 / 编辑 UI。
- [ ] 增加 lifecycle 操作。
- [ ] 添加 Vitest。

### 1.8-D Real API / Runtime Boundary

状态：待开发

- [ ] 验证真实 Webhook HTTP。
- [ ] 验证 Execution persistence。
- [ ] 验证 duplicate event convergence。
- [ ] 验证 authentication failure。
- [ ] 验证删除 / disable 后 endpoint 行为。

### 1.8-E Browser E2E

状态：待开发

- [ ] Browser 创建 Webhook Trigger。
- [ ] Browser inventory / lifecycle。
- [ ] Browser 发起真实 Webhook request。
- [ ] Browser 观察 Execution。
- [ ] Browser 验证 duplicate / rejected contract。

### 1.8-F Final Acceptance

状态：待开发

- [ ] Backend Gate。
- [ ] Frontend Gate。
- [ ] Browser E2E Gate。
- [ ] PROJECT_STATUS 更新。
- [ ] Phase 1.8 验收文档收口。

## 9. 固定开发顺序

严格执行：

```text
1.8-A 需求 / 架构确认
   ↓
1.8-B Backend Domain + API Contract
   ↓
Migration 判定 + Backend tests
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

## 10. 验收门禁

Backend：

```powershell
cd backend
uv run pytest -q
uv run alembic upgrade head
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

Frontend：

```powershell
cd frontend
npm test
npm run build
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\release\01_frontend_regression_gate.ps1
```

Browser：

```powershell
cd frontend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
```

实际测试结果只能在开发者本地执行后记录，不得预填通过。

## 11. 责任 / 时间 / 阻塞

- 责任角色：开发执行。
- 当前状态：1.8-A 完成，1.8-B Backend 核心实现中。
- 开始时间：2026-08-21。
- 目标：完成 Backend Contract、测试和本地 Gate 后进入 Frontend。
- 当前阻塞：无已知阻塞；本地 PostgreSQL / uv 测试尚未在本次远端编辑环境执行。
- 资源依赖：PostgreSQL、现有 Trigger / Workflow Execution Contract；真实 secret 仅使用未提交 `backend/.env`。

## 12. 风险

1. 现有 Trigger Model 已足够表达 Webhook，不应重复建表。
2. Webhook 重复投递必须以数据库持久化唯一约束为最终边界。
3. Webhook authentication 与 AuditLog 不能泄露 secret。
4. 不应把 Webhook 接收接口演变成新的通用消息队列。
5. 不应修改 Phase 1.7 Scheduled Scheduler 以适配新的事件入口。
