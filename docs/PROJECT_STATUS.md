# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.9 Enterprise Integration / Event Infrastructure 开发中**
- 当前任务：**Phase 2.9-E Runtime Integration 第一切片**
- 下一任务：**补齐 Workflow / Agent / Scheduler 关键业务事实覆盖，并收口 2.9-D Real Acceptance**

开发严格基于远端 `main`，不创建功能分支。

## 2. 已完成能力
- Phase 2.7 Advanced Workflow 主线生产能力完成；
- Durable Workflow / Resume / Frontier / Scheduler 基础设施完成；
- Phase 2.8 Delegation Contract、Durable Entity、Claim、Worker Bridge、generation fencing、timeout/cancel、Audit/Trace、B6 multi-worker Runtime 已完成并通过本地 Real Gate；
- Worker shutdown AsyncEngine cancellation-safe disposal 已完成；
- Phase 2.9-A Event Contract 已实现；
- Phase 2.9-B Durable Event Persistence 已实现；
- Phase 2.9-C Reliable Delivery 已通过真实 PostgreSQL Gate；
- Phase 2.9-D Webhook Provider / Destination / Subscription / Fan-out / Delivery Worker / Security / Audit / Replay 第一实现链路已完成，Real Acceptance 待最终收口；
- Phase 2.9-E Runtime Integration 已启动，统一 Runtime Event Publisher 已接入 Workflow / Agent / Scheduler 第一批关键业务事实。

## 3. Phase 2.8 验收基线
开发者本地正式 B6 Gate 已全部通过：38 个 Unit/Contract 测试、870 个 Backend 回归测试（3 skipped）、Migration head 0039、5 个 Real HTTP + PostgreSQL 多 Worker 测试全部通过。

## 4. Phase 2.9 当前实现

### 2.9-A Event Contract
状态：**已实现**。

### 2.9-B Durable Event Persistence
状态：**已实现**。

### 2.9-C Reliable Delivery
状态：**已完成真实 PostgreSQL 验收**。

开发者最新已验证结果：

```text
PostgreSQL concurrency/recovery tests → 5 passed
Targeted delivery unit regression → 15 passed
[PASS] Phase 2.9-C Reliable Delivery PostgreSQL Real Gate completed.
```

### 2.9-D Webhook Integration
状态：**实现链路已完成，Real Acceptance 待最终收口**。

已具备：
- HTTPS / SSRF / endpoint security；
- Secret Resolver；
- Provider / Destination / Subscription / Fan-out；
- PostgreSQL Delivery Fact、lease、retry、dead-letter；
- Delivery Audit 与 Replay；
- Webhook Delivery Worker concurrency/backpressure/graceful shutdown；
- `run_worker.py` Worker Runtime 集成；
- `02_webhook_delivery_real_gate.ps1` Real Acceptance Gate。

### 2.9-E Runtime Integration
状态：**第一实现切片已完成，继续扩展中**。

统一入口：

```text
backend/app/services/integration/publisher.py
```

第一批 Runtime 事件：

```text
Workflow  → workflow.execution.completed
Agent     → agent.execution.started
            agent.execution.completed
            agent.execution.failed
Scheduler → scheduler.trigger.dispatched
```

事件均使用统一 `IntegrationEvent` Contract，并通过事务内 Publisher 写入 Durable `integration_events`。Publisher 不自行 commit；唯一冲突通过 savepoint + 查询收敛。

Workflow completion event 与 Durable Frontier/Execution completion 共用同一数据库事务；Scheduler dispatch event 与 Scheduled Execution/Frontier 创建共用同一数据库事务；Agent lifecycle event 与既有 Observability Execution lifecycle 共用当前事务。

## 5. 下一任务

### 2.9-E Runtime Event Coverage

继续实现：
1. Workflow `created / started / failed / cancelled / retry_requested / resume_requested`；
2. Agent Tool / Retrieval / Model Provider 关键事实；
3. Scheduler lease / contention / misfire / recovery 结果事件；
4. Integration Event tenant-scoped 查询与运维视图；
5. Event schema/version 稳定化与 Runtime Integration Real Acceptance。

### 2.9-D Real Acceptance

与 2.9-E 并行收口既有 Webhook Real Gate，但不因此阻塞 Runtime Integration 的代码实现。

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
2.9-D Webhook Integration                   🔄 Real Acceptance 收口
        ↓
2.9-E Runtime Integration                   🔄 第一切片完成
```

所有实现仍遵循 Contract → Migration → Backend → Unit/Integration/Contract → Real API → Acceptance。
