# 项目状态

## 1. 当前基线
- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.9 Enterprise Integration / Event Infrastructure 验收收口中**
- 当前任务：**Runtime Integration Real Acceptance + 2.9-D Webhook Real Acceptance**
- 下一任务：**Acceptance 全通过后冻结 Phase 2.9 Event Contract，并进入企业运维/IAM/Observability 长期任务**

开发严格基于远端 `main`，不创建功能分支。

## 2. 已完成能力
- Phase 2.7 Advanced Workflow 主线生产能力完成；
- Durable Workflow / Resume / Frontier / Scheduler 基础设施完成；
- Phase 2.8 Delegation Contract、Durable Entity、Claim、Worker Bridge、generation fencing、timeout/cancel、Audit/Trace、B6 multi-worker Runtime 已完成并通过本地 Real Gate；
- Worker shutdown AsyncEngine cancellation-safe disposal 已完成；
- Phase 2.9-A Event Contract 已实现；
- Phase 2.9-B Durable Event Persistence 已实现；
- Phase 2.9-C Reliable Delivery 已通过真实 PostgreSQL Gate；
- Phase 2.9-D Webhook Provider / Destination / Subscription / Fan-out / Delivery Worker / Security / Audit / Replay 实现链路已完成，真实 HTTP + PostgreSQL Acceptance 已具备独立 Gate；
- Phase 2.9-E Workflow / Agent Tool / Retrieval / Model Provider / Scheduler Runtime 已具备统一 Integration Event 发布边界；
- Integration Event 已提供 tenant-scoped operations query API 与分页/事件过滤。

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
状态：**Real Acceptance 收口中**。

### 2.9-E Runtime Integration
状态：**核心业务事实接入完成，Real Acceptance 收口中**。

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

### Runtime Integration Acceptance
新增：

```text
backend/tests/api_real/test_runtime_integration_acceptance.py
backend/scripts/test/phase-2.9/03_runtime_integration_real_gate.ps1
```

Acceptance 自动生成两个 tenant，并验证 Workflow / Tool / Retrieval / Model / Scheduler 五类事件持久化到 PostgreSQL Durable Integration Event；同时验证 tenant-scoped predicate 不允许 Tenant B 读取 Tenant A 的事件。事件 payload 不包含 prompt、completion 或 Retrieval 正文等敏感业务内容。

该 Gate 不启动或停止 API、Worker、Scheduler、Redis、PostgreSQL，也不要求手工输入测试数据；数据库必须由本地环境预先提供。

### Webhook Real Acceptance

```text
backend/scripts/test/phase-2.9/02_webhook_delivery_real_gate.ps1
```

验证真实 localhost HTTP Receiver、PostgreSQL Delivery lease/state、签名、Delivery Audit、Replay 与重复投递链路。脚本路径解析已统一以 `backend/scripts/test/phase-2.9` 为基准，避免 Windows PowerShell 从调用目录推断错误项目根目录。

### Integration Operations View

```text
GET /api/v1/runtime/integration-events
```

查询始终使用当前 JWT `tenant_id`，客户端不能指定任意 tenant；支持分页以及 `event_type / source / status / subject / trace_id / request_id` 过滤。

## 5. Acceptance 收口任务

1. Runtime Integration Real Acceptance：真实 PostgreSQL 验证五类 runtime facts；
2. Tenant isolation Acceptance：验证不同 tenant 无法读取彼此 Integration Event；
3. Webhook Real Acceptance：验证 Runtime Event → Fan-out → Delivery Worker → retry/dead-letter/audit/replay；
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
2.9-D Webhook Integration                   🔄 Real Acceptance 收口中
        ↓
2.9-E Runtime Integration                   🔄 Real Acceptance 收口中
```

所有实现仍遵循 Contract → Migration → Backend → Unit/Integration/Contract → Real API → Acceptance。
