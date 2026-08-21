# Phase 1.8 — Event / Webhook Trigger Expansion

> 状态：**正式关闭（1.8-A ～ 1.8-F 全部完成）**

## 1. 目标

将 Trigger 入口从时间驱动扩展到外部事件驱动，形成可治理、可审计、可幂等的 Webhook / Event Trigger 能力。

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

## 2. In Scope

1. Webhook Trigger Domain Contract。
2. Webhook Trigger CRUD / enable / disable / delete。
3. 外部事件入口 API。
4. 身份校验与安全边界。
5. Event Idempotency，重复投递不产生重复 Execution。
6. Webhook → Workflow Execution Backend Real API Contract。
7. Trace / Audit 关联。
8. Frontend Webhook Governance。
9. Browser → Vue → Backend → Webhook → Execution observable contract。

Out of Scope：MQ/Kafka、通用 Event Bus、任意 OAuth 平台、任意代码执行、多 Agent 协作、跨服务分布式任务系统。

## 3. Backend Contract

```text
POST /api/v1/webhooks/{trigger_id}
```

使用 `X-Webhook-Secret`、可选 `Idempotency-Key`、可选 `X-Request-ID`。若没有 Idempotency-Key，则从配置的 `event_id_field` 提取事件身份；两者都不存在返回 `422`。

首次 claim 返回 `202 accepted`；重复投递返回 `200 duplicate`；认证失败 `401`；禁用 Trigger `409`。

Secret 只写入，不从 response 返回；持久化只保存 `secret_hash`。

## 4. Durable Idempotency

优先：

```text
webhook:{trigger_id}:{event_identity}
```

超过 `workflow_executions.idempotency_key` 100 字符时使用 SHA-256 bounded key。最终持久化边界依赖 `(tenant_id, idempotency_key)` 唯一约束，不依赖内存锁。

## 5. Database

Phase 1.8 无新增 Migration；不创建 `webhook_events` 表，也不修改 `0022_workflow_trigger`。

## 6. Frontend / Browser

Frontend 提供 Webhook Trigger 类型、配置、inventory、lifecycle 和 endpoint 展示，但不负责 durable event identity、duplicate 判断、Workflow Execution 创建或 authentication。

Browser E2E 覆盖创建、inventory、Enable/Disable、合法 Webhook、duplicate、错误 secret、删除后 endpoint 不可用。

## 7. 任务

- 1.8-A 需求 / Contract Baseline：完成
- 1.8-B Backend Domain + API：完成
- 1.8-C Frontend API + Governance UI：完成
- 1.8-D Real API / Runtime Boundary：完成
- 1.8-E Browser E2E：完成
- 1.8-F Final Acceptance：完成并正式关闭

## 8. 实际结果

本阶段实际结果与最终验收证据统一记录于 `03-acceptance/PHASE_1_8_ACCEPTANCE.md`；当前 `PROJECT_STATUS.md` 记录最新项目状态。