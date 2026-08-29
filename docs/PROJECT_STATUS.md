# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.9 Enterprise Integration / Event Infrastructure 开发中**
- 当前任务：**2.9-D Webhook Integration 第一实现切片**
- 下一任务：**2.9-D Webhook destination/subscription 持久化与可靠投递编排**

开发严格基于远端 `main`，不创建功能分支。

## 2. 已完成能力
- Phase 2.7 Advanced Workflow 主线生产能力完成；
- Durable Workflow / Resume / Frontier / Scheduler 基础设施完成；
- Phase 2.8 Delegation Contract、Durable Entity、Claim、Worker Bridge、generation fencing、timeout/cancel、Audit/Trace、B6 multi-worker Runtime 已完成并通过本地 Real Gate；
- Worker shutdown AsyncEngine cancellation-safe disposal 已完成；
- Phase 2.9-A Event Contract 已实现；
- Phase 2.9-B Durable Event Persistence 已实现；
- Phase 2.9-C Reliable Delivery 已通过真实 PostgreSQL Gate；
- Phase 2.9-D Webhook Provider 第一实现切片已完成。

## 3. Phase 2.8 验收基线
开发者本地正式 B6 Gate 已全部通过：38 个 Unit/Contract 测试、870 个 Backend 回归测试（3 skipped）、Migration head 0039、5 个 Real HTTP + PostgreSQL 多 Worker 测试全部通过。

## 4. Phase 2.9 当前实现

### 2.9-A Event Contract
状态：**已实现**。

### 2.9-B Durable Event Persistence
状态：**已实现**。

### 2.9-C Reliable Delivery
状态：**已完成真实 PostgreSQL 验收**。

开发者最新本地结果：

```text
PostgreSQL concurrency/recovery tests → 5 passed
Targeted delivery unit regression → 15 passed
[PASS] Phase 2.9-C Reliable Delivery PostgreSQL Real Gate completed.
```

覆盖并发 Claim、租约恢复、fencing、tenant isolation、retry/dead-letter，并确认 `0041_integration_event_delivery_lease` 为 migration head。

### 2.9-D Webhook Integration
状态：**第一实现切片已完成，整体功能仍在开发中**。

新增正式出站 Provider：

```text
backend/app/infrastructure/providers/webhook.py
backend/tests/unit/test_webhook_provider.py
```

已具备统一 Event JSON envelope、事件身份头、幂等头、HMAC-SHA256 签名、HTTPX Client 注入和非 2xx 失败透传。

现有 `WebhookTriggerService` 仍只负责入站 Trigger；`WebhookProvider` 专门负责出站 Integration，两者职责分离。

## 5. 下一任务

### 2.9-D Webhook destination/subscription

继续实现：
1. destination/subscription PostgreSQL 模型与 Migration；
2. tenant boundary、启停状态和 Secret 引用；
3. Durable Event → destination 的正式编排；
4. delivery audit、replay、查询；
5. endpoint allowlist / SSRF 与网络出口策略；
6. Real HTTP + PostgreSQL Acceptance Gate。

完成后才进入 2.9-E Runtime Integration。

## 6. 长期未完成能力
长期企业化能力独立维护在 `docs/05-long-term/`：

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
2.9-B Durable Event Persistence              ✅
        ↓
2.9-C Reliable Delivery                     ✅ Real PostgreSQL Gate
        ↓
2.9-D Webhook Integration                   🔄 Provider 第一切片完成
        ↓
2.9-E Runtime Integration                   ⏳
```

所有实现仍遵循 Contract → Migration → Backend → Unit/Integration/Contract → Real API → Acceptance。
