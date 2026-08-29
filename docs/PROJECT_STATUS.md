# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.9 Enterprise Integration / Event Infrastructure 开发中**
- 当前任务：**Phase 2.9-E Runtime Integration Acceptance 收口准备**
- 下一任务：**Runtime Integration Real Acceptance + 2.9-D Webhook Real Acceptance 统一收口**

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
- Phase 2.9-E Runtime Integration 已完成 Workflow Governance 事件桥接；
- Agent Tool Runtime 已增加统一 Integration Event 发布能力；
- Knowledge Retrieval 已增加统一 Integration Event 发布入口；
- Model Provider Runtime 已增加事务内 invocation event boundary；
- Scheduler Runtime 已把 lease acquired、dispatch、misfire、recovery、failure facts 写入 Durable Integration Event；lease acquired 与 lease claim 在同一数据库事务中提交；
- Integration Event 已提供强制 tenant-scoped operations query API 与分页/事件类型/source/status/subject/trace/request 过滤。

## 3. Phase 2.8 验收基线
开发者本地正式 B6 Gate 已全部通过：38 个 Unit/Contract 测试、870 个 Backend 回归测试（3 skipped）、Migration head 0039、5 个 Real HTTP + PostgreSQL 多 Worker 测试全部通过。

## 4. Phase 2.9 当前实现

### 2.9-A Event Contract
状态：**已实现**。

### 2.9-B Durable Event Persistence
状态：**已实现**。

### 2.9-C Reliable Delivery
状态：**已完成真实 PostgreSQL 验收**。

### 2.9-D Webhook Integration
状态：**实现链路已完成，Real Acceptance 待最终收口**。

### 2.9-E Runtime Integration
状态：**核心业务事实接入完成，进入 Acceptance 收口阶段**。

统一入口：

```text
backend/app/services/integration/publisher.py
```

当前 Runtime Event Contract：

```text
Workflow  → workflow.execution.created
            workflow.execution.completed
            workflow.execution.failed
            workflow.execution.cancelled
            workflow.execution.retry_requested
            workflow.execution.resume_requested

Agent     → agent.execution.started
            agent.execution.completed
            agent.execution.failed
            agent.tool.succeeded
            agent.tool.failed
            agent.retrieval.succeeded
            agent.retrieval.failed
            agent.model.succeeded
            agent.model.failed

Scheduler → scheduler.trigger.dispatched
            scheduler.lease.acquired
            scheduler.dispatched
            scheduler.contention
            scheduler.misfire
            scheduler.recovery
            scheduler.failed
```

### Agent Tool / Retrieval
Tool 与 Retrieval 已具备统一 publisher 接口；事件 payload 仅记录运行身份、来源和计数/错误码，不写入 authorization、token、prompt、completion 或检索正文等敏感内容。

### Model Provider
新增 `ModelProviderInvocationService` 作为实际 Provider invocation boundary：调用 `ModelProvider.complete()` 成功/失败后，在当前数据库事务内写入 `agent.model.succeeded` / `agent.model.failed`。调用方负责最终 commit，Invocation Service 不自行提交事务。

### Scheduler
`ScheduledTriggerScheduler.tick_once()` 已注入 `RuntimeIntegrationEventPublisher`。lease acquisition 与 `scheduler.lease.acquired` 同事务提交；创建 Execution 后产生 `scheduler.dispatched`；发生 misfire 时产生 `scheduler.misfire` 与 `scheduler.recovery`；异常释放 lease 后产生 `scheduler.failed`。事件幂等键沿用 trigger/slot 空间，避免多实例重复事实。

### Integration Operations View
新增：

```text
GET /api/v1/runtime/integration-events
```

查询始终使用当前 JWT `tenant_id`，客户端不能指定任意 tenant；支持分页以及 `event_type / source / status / subject / trace_id / request_id` 过滤。该接口为后续管理后台 Runtime/Event Operations View 提供稳定查询边界。

## 5. Acceptance 收口任务

1. Runtime Integration Real Acceptance：验证 Workflow / Agent Tool / Retrieval / Model Provider / Scheduler 关键事实真实写入 PostgreSQL Durable Event；
2. Tenant isolation Acceptance：验证不同 tenant 无法读取彼此 Integration Event；
3. Webhook Real Acceptance：验证 Runtime Event → Fan-out → Delivery Worker → retry/dead-letter/audit/replay 全链路；
4. schema/version 稳定化，并冻结 Phase 2.9 Event Contract；
5. Acceptance 全部通过后，Phase 2.9 进入完成评审，并转入后续 Enterprise Operations / IAM / Observability 等长期任务。

## 6. 长期未完成能力
长期企业化能力独立维护在 `docs/05-long-term/`：

| ID | 长期能力 | 状态 |
|---|---|---|
| LT-01 | Enterprise Integration / Event Infrastructure | **Phase 2.9 Acceptance 收口中** |
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
2.9-E Runtime Integration                   🔄 Acceptance 收口准备
```

所有实现仍遵循 Contract → Migration → Backend → Unit/Integration/Contract → Real API → Acceptance。
