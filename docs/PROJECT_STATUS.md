# 项目状态

## 1. 当前基线

- Repository：`AnRedSky/enterprise-ai-agent-platform`
- Branch：`main`
- 当前阶段：**Phase 2.8 Multi-Agent Collaboration / Runtime Integration**
- 当前任务：**B6 Delegation Multi-Worker Runtime acceptance**

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
- B4 timeout / cancel / parent semantics 已完成并由开发者本地 Real Gate 验收通过；
- Runtime Session / Execution terminalization / Model Profile Snapshot / Frontier heartbeat 锁序问题已完成修复；
- Scheduler 对单节点顺序 Workflow 的空 `edges` 语义已与 DAG Runtime 对齐；
- B5 Delegation Audit / Trace 基础闭环已实现，创建与取消事件已写入 AuditLog / WorkflowTraceEvent；
- Worker shutdown AsyncEngine cancellation-safe disposal 已完成并通过 B5 Unit Gate；
- B6 已补齐 Delegation 从 pending fact 到 Durable Frontier Worker dispatch 的正式运行链路。

## 3. 最新本地验收证据

开发者在 `352f737a` 基线完成 B5：

```text
B5 Worker shutdown + Delegation lifecycle Unit   27 passed
Backend regression                                860 passed, 3 skipped, 50 deselected
Migration/head                                   0039_workflow_node_execution_tenant_trigger (head)
B5 Real Gate                                     4 passed
```

B5 已达到本地 Gate 通过条件，允许进入 B6。

## 4. B6 实现与当前修复

B6 初始实现已把 pending Delegation 接入 Durable Frontier Worker，但本地 Real Gate 暴露两个运行时问题：

1. 多 Worker 两轮 dispatch 只消费了 2/4 个 Delegation；根因是 Delegation Claim 成功提交后，dispatch 再通过全局 tenant Frontier 扫描重新寻找刚创建的 Frontier，存在候选集合变化导致的空转窗口。
2. B2 旧 Real API 测试直接调用 `execute_claimed_execution()`，绕过了 B6 正式 Durable Frontier dispatch 边界；在 Frontier terminalization fencing 收紧后，该测试错误地让 Runtime 在仍存在 active Frontier 时直接 terminalize Execution。

当前修复将 Delegation Claim → Worker Execution → Frontier 激活改为确定性链路：Claim 返回的 `worker_execution_id` 直接定位新建 Frontier，并在同一 Worker 调度流程中建立 Frontier lease；同时 B2 Real API 测试改为通过正式 `WorkflowWorker.claim_one_frontier()` + `execute_frontier()` 验证 Target Agent Runtime，不再绕过 Durable Frontier。

随后发现默认 Worker 入口契约与 Delegation Runtime Entry 之间还存在边界冲突：`d44d6b86` 将公开 `WorkflowWorker` 错误切换为 `DurableFrontierWorkflowWorker`，导致 Backend default regression 的 3 个默认入口契约测试失败；直接恢复 Planner-driven 默认入口又会让 Delegation Frontier 进入普通 Planner execution，绕过 `AgentDelegationRuntimeBridge`。

本轮代码修复已完成两点：

1. 恢复 `WorkflowWorker = PlannerDrivenDurableFrontierWorkflowWorker` 作为正式默认入口；
2. `PlannerDrivenDurableFrontierWorkflowWorker.execute_frontier()` 对已 Claim Delegation 的 Frontier 路由到父 `DurableFrontierWorkflowWorker.execute_frontier()`，从而进入唯一 `runtime_entry.execute_claimed_execution()`；普通 Workflow Frontier 继续走 Planner-driven 路径。

两条路径共享同一个 Claim、Frontier、Lease、WorkflowRuntime 与状态模型，不新增第二套 Execution / Delegation / Retry / Recovery 状态机。

开发者本次反馈中还出现 Provider `503 Service Unavailable`。从调用栈看，请求落入本地 OpenAI-compatible endpoint，且实际执行的是父 Workflow fixture 的 prompt；这与 Planner-driven Worker 未区分 Delegation Frontier 的职责边界问题一致。本轮修复已将 Delegation Frontier 路由回 canonical Runtime Entry，必须通过新的本地 Real Gate 结果最终确认。

错误根因与修复记录：

- `docs/04-errors/2026-08-29-phase-2-8-b6-worker-entrypoint-and-delegation-runtime.md`

## 5. B6 自动化验收

正式入口：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\phase-2.8\06_delegation_multi_worker_runtime_gate.ps1
```

Gate 自动生成测试用户、Token、tenant、ID 与测试数据；Gate 本身不启动、重启或停止任何服务，只验证 PostgreSQL、Redis、Backend API 本地前置条件。

验收顺序：

```text
[0] prerequisite service verification
    ↓
[1] Delegation Claim + Worker dispatch Unit/Contract
    ↓
[2] Backend default regression
    ↓
[3] Alembic upgrade/head
    ↓
[4] Real HTTP + PostgreSQL multi-worker Durable Frontier Runtime
```

本轮代码修复后必须重新实际执行 Gate，不能根据代码状态预填 Passed。

## 6. 下一主线任务

```text
B6 Delegation Multi-Worker Runtime acceptance
    ↓
Phase 2.8 closure
    ↓
Phase 2.9 Enterprise Integration / Event Infrastructure Contract
```

在 B6 Real Gate 实际通过前，不提前进入 Phase 2.9 功能开发。
