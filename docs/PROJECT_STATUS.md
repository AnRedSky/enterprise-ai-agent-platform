# 项目状态

## 1. 当前基线

- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.9 Enterprise Integration / Event Infrastructure 开发中**
- 当前任务：**2.9-A Event Contract 第一实现切片**
- 下一任务：**2.9-B Durable Event Persistence**

开发严格基于远端 `main`，不创建功能分支。

## 2. 已完成能力

- Phase 2.7 Advanced Workflow 主线生产能力完成；
- Durable Workflow / Resume / Frontier / Scheduler 基础设施完成；
- Phase 2.8-A Delegation Contract 已冻结；
- `AgentDelegation` Durable Entity / Repository / Service / API 已完成；
- tenant / Agent version / permission / idempotency / depth / active-count / timeout / model budget 已实现；
- B1 Atomic Claim 已完成并通过本地真实 HTTP + PostgreSQL 双 Worker 并发 Gate；
- B2 Worker Execution Bridge 已完成，复用既有 Workflow Worker / WorkflowRuntime；
- B3 Delegation completion/failure generation fencing 已完成；
- B4 timeout / cancel / parent semantics 已完成并有本地 Runtime / Real API 验收证据；
- Runtime Session / Execution terminalization / Model Profile Snapshot / Frontier heartbeat 锁序问题已完成修复；
- Scheduler 对单节点顺序 Workflow 的空 `edges` 语义已与 DAG Runtime 对齐；
- B5 Delegation Audit / Trace 基础闭环已实现，创建与取消事件已写入 AuditLog / WorkflowTraceEvent；
- Worker shutdown AsyncEngine cancellation-safe disposal 已完成并通过 targeted Unit Gate；
- B6 已补齐 Delegation 从 pending fact 到 Durable Frontier Worker dispatch 的正式运行链路；
- B6 多 Worker contention、drain 时序、Worker shutdown cleanup 及 Windows PowerShell Worker/Scheduler 隔离检查已完成修复；
- Phase 2.8 Runtime Integration 已达到本地 Real Gate 收口条件；
- Phase 2.9-A 已建立统一 Enterprise Integration Event Contract 第一实现切片。

## 3. 最新 Phase 2.8 验收基线

最新开发者本地执行的正式 B6 Gate 已全部通过：

```text
[1/4] Delegation Claim + Worker dispatch Unit/Contract
38 passed in 1.08s

[2/4] Backend default regression
870 passed, 3 skipped, 52 deselected in 34.61s

[3/4] Migration/head verification
0039_workflow_node_execution_tenant_trigger (head)

[4/4] Real HTTP + PostgreSQL multi-worker Durable Frontier Runtime
5 passed in 7.48s

[PASS] Phase 2.8 B6 multi-worker Delegation Runtime gate completed.
```

该结果继续作为 Phase 2.8 Runtime Integration 的历史验收基线；除非出现新的实际回归，不重复修改已经通过的 Claim、Worker dispatch、timeout/cancel 或 shutdown cleanup 路径。

## 4. Phase 2.9 当前实现

### 2.9-A Event Contract

状态：**第一切片已实现，单元测试待开发者本地执行确认。**

新增统一事件领域契约：

```text
backend/app/services/integration/
├── __init__.py
└── contract.py
```

事件信封当前冻结以下字段：

- `event_id`
- `tenant_id`
- `event_type`
- `schema_version`
- `source`
- `subject`
- `idempotency_key`
- `occurred_at`
- `request_id`
- `trace_id`
- `payload`
- `metadata`

幂等作用域：

```text
tenant_id + source + event_type + idempotency_key
```

该实现只承担领域 Contract 与校验，不包含数据库、HTTP、Scheduler、Worker 或消息中间件实现。

对应测试：

```text
backend/tests/unit/test_integration_event_contract.py
```

### 2.9-B Durable Event Persistence

下一任务：实现 PostgreSQL Durable Event Fact，并冻结状态机、投递次数、失败信息、下一次投递时间和数据库幂等唯一约束，然后建立 Alembic Migration。

当前不得直接引入 Kafka、MQ、Event Bus 或第二套 Outbox。

## 5. 长期未完成能力

长期企业化能力继续独立维护在 `docs/05-long-term/`。

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

长期任务索引：`docs/05-long-term/README.md`。

## 6. Phase 2.9 开发顺序

```text
2.9-A Event Contract                         ✅ 第一切片实现
        ↓
2.9-B Durable Event Persistence              ⏳ 下一任务
        ↓
2.9-C Reliable Delivery                     ⏳
        ↓
2.9-D Webhook Integration                   ⏳
        ↓
2.9-E Runtime Integration                   ⏳
```

每一步均必须遵循 Contract → Migration（如涉及数据库）→ Backend → Unit/Integration/Contract → Real API → Acceptance 的顺序。

## 7. 文档基线

- `docs/01-governance/DEVELOPMENT.md`：唯一工程开发准则；
- `docs/02-phases/PHASE_2_9.md`：当前 Phase 2.9 开发计划与实现切片；
- `docs/05-long-term/LT-01-ENTERPRISE-INTEGRATION-EVENT-INFRASTRUCTURE.md`：长期 LT-01 能力全量 backlog；
- `docs/05-long-term/README.md`：长期任务索引；
- `docs/03-acceptance/`：真实验收事实；
- `docs/04-errors/`：已发生并完成分析的工程错误。

当前长期任务与当前 Phase 已保持独立：LT-01 记录长期能力全貌，Phase 2.9 只记录已经正式立项并进入实现的任务。
