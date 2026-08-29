# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.9 Enterprise Integration / Event Infrastructure 开发中**
- 当前任务：**Phase 2.9-E Runtime Integration 第三切片**
- 下一任务：**完成 Scheduler runtime facts wiring，并收口 Runtime Integration Acceptance**

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
- Model Provider Runtime Event helper 已进入统一 Publisher；
- Scheduler lease / contention / misfire / recovery 事件模型已进入统一 Publisher，下一切片完成 Scheduler Runtime 实际事务接入。

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
状态：**第三实现切片开发中**。

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
            scheduler.lease.*
            scheduler.contention
            scheduler.misfire
            scheduler.recovery
```

### Agent Tool
`ToolRuntimeService` 现在可以通过注入 `RuntimeIntegrationEventPublisher`，在 Tool 成功/失败后写入 Durable Integration Event。事件只携带 execution/agent/tool 身份与错误码，不携带 authorization、token、prompt、Tool result 等敏感内容。

### Agent Retrieval
`KnowledgeRetrievalService` 增加可选 Runtime Integration Publisher，并支持由 Agent Runtime 显式提供 `tenant_id / execution_id / agent_id / knowledge_base_id`，从而在检索完成后产生 tenant-scoped Retrieval business fact。检索内容本身不进入事件 payload。

### Model Provider
Publisher 已提供 `publish_agent_model()`，用于统一记录 Provider/Profile 调用成功或失败事实；事件不写入 prompt/completion 等模型内容。下一步将其接入实际 Model Provider invocation transaction。

### Scheduler
Publisher 已提供 lease / contention / misfire / recovery / dispatched 等标准化事件接口。Scheduler Runtime 当前已有 PostgreSQL lease、slot、contention、misfire/recovery 计算与 dispatch 事务边界；下一切片将把这些实际状态转换接入同一事务内 Durable Integration Event，保持 Scheduler 业务事实与 Event 原子提交。

## 5. 下一任务

1. Scheduler Runtime 实际接入 `lease.claimed / lease.released / contention / misfire / recovery`；
2. Model Provider invocation 实际接入 succeeded/failed/timeout facts；
3. Retrieval Runtime 的 Agent transaction caller 全链路接入；
4. Integration Event tenant-scoped query / operations view；
5. schema/version 固化；
6. Runtime Integration Real Acceptance；
7. 与此同时收口 2.9-D Webhook Real Acceptance。

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
2.9-E Runtime Integration                   🔄 第三切片开发中
```

所有实现仍遵循 Contract → Migration → Backend → Unit/Integration/Contract → Real API → Acceptance。
