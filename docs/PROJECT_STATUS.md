# 项目状态

## 1. 当前基线

- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.9 Enterprise Integration / Event Infrastructure 开发中**
- 当前任务：**2.9-C Reliable Delivery 第一实现切片**
- 下一任务：**2.9-D Webhook Integration**

开发严格基于远端 `main`，不创建功能分支。

## 2. 已完成能力

- Phase 2.7 Advanced Workflow 主线生产能力完成；
- Durable Workflow / Resume / Frontier / Scheduler 基础设施完成；
- Phase 2.8 Delegation Contract、Durable Entity、Claim、Worker Bridge、generation fencing、timeout/cancel、Audit/Trace、B6 multi-worker Runtime 已完成并通过本地 Real Gate；
- Worker shutdown AsyncEngine cancellation-safe disposal 已完成；
- Phase 2.9-A Event Contract 已实现；
- Phase 2.9-B Durable Event Persistence 已实现第一切片；
- Phase 2.9-C Reliable Delivery 已实现第一切片。

## 3. Phase 2.8 验收基线

开发者本地正式 B6 Gate 已全部通过：38 个 Unit/Contract 测试、870 个 Backend 回归测试（3 skipped）、Migration head 0039、5 个 Real HTTP + PostgreSQL 多 Worker 测试全部通过。

## 4. Phase 2.9 当前实现

### 2.9-A Event Contract

状态：**已实现**。

统一事件信封包含 `event_id`、`tenant_id`、`event_type`、`schema_version`、`source`、`subject`、`idempotency_key`、`occurred_at`、`request_id`、`trace_id`、`payload`、`metadata`。幂等作用域为 `tenant_id + source + event_type + idempotency_key`。

### 2.9-B Durable Event Persistence

状态：**已实现第一切片，待开发者本地数据库验收**。

新增 `integration_events` PostgreSQL Durable Event Fact、Repository、0040 Migration 和单元测试。

### 2.9-C Reliable Delivery

状态：**已实现第一切片，待开发者本地验收**。

当前包含：

- PostgreSQL `FOR UPDATE SKIP LOCKED` 原子 Claim；
- Worker lease owner / expiry；
- 过期租约恢复；
- attempt count；
- delivered terminal state；
- capped exponential retry；
- retry exhaustion 后 `dead_letter`；
- 外部 Sender 依赖注入；
- 0041 Migration。

当前实现不绑定 Redis、Kafka、MQ 或具体 Webhook Provider。

尚未声明 Real API / 并发数据库验收通过，必须由开发者本地执行。

## 5. 下一任务

### 2.9-D Webhook Integration

将现有 Webhook Trigger 能力接入 Durable Event Delivery，统一 endpoint、签名、事件版本、幂等、回放和 delivery audit，并避免复制已有 Trigger Service。

## 6. 长期未完成能力

长期企业化能力继续独立维护在 `docs/05-long-term/`：

| ID | 长期能力 | 状态 |
|---|---|---|
| LT-01 | Enterprise Integration / Event Infrastructure | **Phase 2.9 开发中** |
| LT-02 | Enterprise IAM / SSO / Identity Federation | 待立项 |
| LT-03 | Enterprise Operations Console | 待立项 |
| LT-04 | API / Developer Platform | 待立项 |
| LT-05 | Observability / SRE | 待立项 |
| LT-06 | Security / Secrets / Policy | 待立项 |
| LT-07 | Agent Evaluation / Quality | 待立项 |
| LT-08 | Cost / Quota / Billing | 待立项 |
| LT-09 | Agent Asset / Marketplace | 候选 |
| LT-10 | Production Deployment / HA / Operations | 待立项 |

## 7. Phase 2.9 顺序

```text
2.9-A Event Contract                         ✅
        ↓
2.9-B Durable Event Persistence              ✅ 第一切片
        ↓
2.9-C Reliable Delivery                     ✅ 第一切片
        ↓
2.9-D Webhook Integration                   ⏳ 下一任务
        ↓
2.9-E Runtime Integration                   ⏳
```

所有实现仍遵循 Contract → Migration → Backend → Unit/Integration/Contract → Real API → Acceptance。
