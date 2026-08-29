# 项目状态

## 1. 当前基线

- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.8 Multi-Agent Collaboration / Runtime Integration 已完成，正在文档收口**
- 当前任务：**Phase 2.8 Closure / Phase 2.9 Contract 前置评估**
- 下一主线：**Phase 2.9 Enterprise Integration / Event Infrastructure Contract**

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
- B6 多 Worker contention、drain 时序、Worker shutdown cleanup 及 Windows PowerShell Worker/Scheduler 隔离检查已完成修复。

## 3. 最新本地验收证据

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

因此 **B6 已达到本地 Real Gate 通过条件，Phase 2.8 Runtime Integration 已达到收口条件**。

## 4. B6 实现与问题闭环

B6 开发期间本地 Real Gate 暴露并完成以下工程问题修复：

1. 多 Worker 两轮 dispatch 只消费部分 Delegation：根因是 PostgreSQL Claim contention 与固定轮次时序组合导致合法竞争被错误解释为任务未消费；已改为有界窗口内安全 drain；
2. B2 Real API 测试绕过正式 Durable Frontier dispatch 边界：已改为通过正式 `WorkflowWorker` Frontier Claim / Execute 边界验证 Target Agent Runtime；
3. Worker 关闭阶段 AsyncEngine / asyncpg connection close 在主 Task cancellation 下出现 `CancelledError`：已使用独立 cleanup Task + `asyncio.shield()` 保证底层连接池清理完成，并恢复原 cancellation 语义；
4. Real Gate 存在外部 Worker/Scheduler 消费测试 Delegation 的环境污染风险：已增加项目路径感知的 Windows PowerShell 进程隔离检查；Gate 不自动启动、停止或重启服务；
5. Windows PowerShell 进程检测曾存在正则字符串引用解析错误：已改为稳定的路径感知匹配实现。

对应错误记录：

- `docs/04-errors/2026-08-29-phase-2-8-b6-worker-entrypoint-and-delegation-runtime.md`
- `docs/04-errors/2026-08-29-phase-2-8-b6-multi-worker-acceptance-contention.md`
- `docs/04-errors/2026-08-29-worker-async-engine-shutdown-cancelled-error.md`

B6 相关修复提交链已经完成闭环，最终以实际 Real Gate 通过结果作为验收依据，不以历史失败记录覆盖当前状态。

## 5. Phase 2.8 当前阶段判断

```text
Phase 2.8-A Delegation Contract                    ✅ 完成
B1 Atomic Claim                                    ✅ 完成
B2 Worker Execution Bridge                         ✅ 完成
B3 Completion/Failure Generation Fencing           ✅ 完成
B4 Timeout / Cancel / Parent Semantics             ✅ 完成
B5 Audit / Trace                                   ✅ 完成
B6 Multi-Worker Durable Frontier Runtime            ✅ 完成
Phase 2.8 Runtime Integration                      ✅ 收口
```

当前没有证据表明 B6 仍存在未解决的 Runtime 阻塞问题。除非出现新的实际回归，不再重复修改已经通过的 Claim、Worker dispatch、timeout/cancel 或 shutdown cleanup 路径。

## 6. 长期未完成能力

长期企业化能力已从当前 Phase 文档中独立拆出，统一维护在 `docs/05-long-term/`，不作为 Phase 2.8 的未完成任务：

| ID | 长期能力 | 状态 |
|---|---|---|
| LT-01 | Enterprise Integration / Event Infrastructure | 待立项 |
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

这些 LT 文档只记录企业级能力缺口、长期目标和拆解，不代表当前已经冻结 Contract 或已经进入开发。正式进入开发后，再建立对应 `docs/02-phases/PHASE_x_y.md`。

## 7. Phase 2.9 进入前置条件

Phase 2.9 当前仍是**候选/前置评估状态**，尚未冻结 Contract，也未开始功能开发。进入正式开发前必须：

1. 盘点现有 Event、Webhook、Trigger、Audit、Trace、Outbox 等基础设施；
2. 确认是否已有正式 Integration / Event Infrastructure 领域实现，禁止重复创建平行 Service / Repository / Runtime / Provider；
3. 根据真实企业业务场景确定可靠性、幂等、投递、顺序、重试、隔离和可观测边界；
4. 完成 Contract 决策后建立正式 `PHASE_2_9.md` 与对应 Acceptance 入口；
5. 涉及数据库结构时必须 Migration-first，并实际验证 `uv run alembic upgrade head`；
6. 遵循 Contract → Migration → Backend implementation → Unit/Integration/Contract → Real API → Acceptance 的工程顺序。

**不得因为 Phase 2.8 已收口而直接引入 Kafka、MQ、Event Bus 或 Outbox；技术选型必须从已冻结的业务 Contract 和真实可靠性需求出发。**

## 8. 当前文档基线

已完成本轮长期任务分类同步：

- `docs/05-long-term/README.md`
- `docs/05-long-term/LT-01-ENTERPRISE-INTEGRATION-EVENT-INFRASTRUCTURE.md`
- `docs/05-long-term/LT-02-ENTERPRISE-IAM-SSO-IDENTITY.md`
- `docs/05-long-term/LT-03-ENTERPRISE-OPERATIONS-CONSOLE.md`
- `docs/05-long-term/LT-04-API-DEVELOPER-PLATFORM.md`
- `docs/05-long-term/LT-05-OBSERVABILITY-SRE.md`
- `docs/05-long-term/LT-06-SECURITY-SECRETS-POLICY.md`
- `docs/05-long-term/LT-07-AGENT-EVALUATION-QUALITY.md`
- `docs/05-long-term/LT-08-COST-QUOTA-BILLING.md`
- `docs/05-long-term/LT-09-AGENT-ASSET-MARKETPLACE.md`
- `docs/05-long-term/LT-10-PRODUCTION-DEPLOYMENT-HA-OPERATIONS.md`
- `docs/01-governance/DOCUMENTATION.md`

开发治理仍以 `docs/01-governance/DEVELOPMENT.md` 为唯一工程规则入口；文档分类与状态管理以 `docs/01-governance/DOCUMENTATION.md` 为准。
