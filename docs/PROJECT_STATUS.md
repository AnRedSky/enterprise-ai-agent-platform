# 项目开发进度

> 本文只记录项目任务进度、实际验收结果、阻塞项和下一步任务。工程开发规则统一维护在 `docs/DEVELOPMENT.md`。阶段计划维护在对应 `docs/PHASE_*.md`。

## 1. 当前主线

- 主分支：`main`
- 项目地址：`https://github.com/AnRedSky/enterprise-ai-agent-platform.git`
- 开发方式：所有功能直接在 `main` 开发与提交
- Phase 1.5：**已完成**
- Phase 1.6：**已完成并正式关闭**
- Phase 1.7：**已完成并正式关闭**
- 当前阶段：**Phase 1.8 Event / Webhook Trigger Expansion**
- 当前任务：**Phase 1.8-B Backend Domain + API 已进入实现，Migration 判定完成**
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
| **Phase 1.8-A** | **已完成** | Event / Webhook Trigger 需求、领域边界、Backend Contract 原则、Security / Idempotency、三层 Gate 已确认 |
| **Phase 1.8-B** | **进行中** | Trigger Model / Schema / Service 审计完成；确认复用 `workflow_triggers` + `workflow_executions`，本批无需新增 migration；Webhook config / endpoint / authentication / durable idempotency 已进入实现 |
| **Phase 1.8** | **进行中** | Event / Webhook Trigger Expansion |

## 3. Phase 1.7-A/B 基线与 Runtime 结论

当前 main 已包含 Scheduled Trigger、Scheduler、interval slot、deterministic idempotency key、bounded recovery、workflow execution persistence 与 runtime execution 闭环。Scheduler 使用 PostgreSQL 数据库 unique constraint `(tenant_id, idempotency_key)` 作为同 slot 多 worker 的持久化收敛边界。

## 4. Phase 1.7 最终验收

Phase 1.7-A～D 全部完成；Backend、Frontend、Browser / Frontend-Backend E2E 三层 Gate 独立通过；Scheduler → Execution 真实边界完成验收；Phase 1.7 正式关闭。

## 5. Phase 1.8 需求 / 架构确认

Phase 1.8 采用“Event / Webhook Trigger Expansion”作为基于已完成 Scheduled Trigger 能力的下一步工程方案，详细计划维护在 `docs/PHASE_1_8.md`。

### 目标

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

### 1.8-B 审计与 Migration 判定

审计结论：

1. `workflow_triggers` 已具备 `trigger_type + config + tenant/workflow/status` 表达能力，无需新增 Webhook 专用 Trigger 表或字段；该模型来自既有 `0022_workflow_trigger` migration。
2. `workflow_executions` 已具备 `(tenant_id, idempotency_key)` 唯一持久化边界，可直接承担 Webhook 重复事件的 durable claim，不新增 `webhook_events` 表。
3. Webhook event identity 采用 `Idempotency-Key`，或从配置的 `event_id_field` 提取；最终 durable key 为 `webhook:{trigger_id}:{event_identity}`。
4. Webhook secret 不以明文持久化，config 中仅保存 SHA-256 `secret_hash`；Trigger API response 不返回 hash。
5. Webhook endpoint 独立于 Scheduled Scheduler：`POST /api/v1/webhooks/{trigger_id}`。
6. Webhook authentication 在 durable claim 前执行；secret/token 不写入 AuditLog / Trace metadata / 普通日志。
7. 本批 **无需新增 Alembic migration**。

### 当前实现范围

- Webhook Trigger type 已加入 Trigger Domain。
- Webhook config contract 已加入 secret / event identity validation。
- Webhook secret 已改为 hash persistence。
- Webhook HTTP endpoint 已注册。
- accepted / duplicate 响应 contract 已建立。
- durable idempotent execution claim 已复用 PostgreSQL unique constraint。
- unit test 已覆盖 config hash、secret verification、非法 auth mode / secret 长度。

### 测试状态

代码已提交到 `main`，但当前环境未执行本地 PostgreSQL / `uv` 测试，因此**不得将 Backend Gate 标记为通过**。下一步必须在开发环境执行：

```powershell
cd backend
uv run pytest -q
uv run alembic upgrade head
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

实际结果通过后再进入 1.8-C。

## 6. 下一步

```text
1.8-B Backend Contract 本批实现
        ↓
本地 Backend Gate / Real API 验证
        ↓
补齐 Webhook API Contract / Real API 覆盖
        ↓
1.8-C Frontend API Types + Vitest
        ↓
Frontend UI
        ↓
1.8-D Real API / Runtime Boundary
        ↓
1.8-E Browser E2E
        ↓
1.8-F Final Acceptance
```
