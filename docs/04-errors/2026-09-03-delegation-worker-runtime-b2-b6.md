# Phase 2.10-II Delegation Worker B2/B6 根因记录

日期：2026-09-03

## 1. B2 Worker Runtime terminal transition

### 现象

Real API B2 中出现 `AgentDelegation=running`、`WorkflowExecution=running`，测试期待 `completed`。

### 根因

`claim_delegation(commit=False)` 创建的 Durable Frontier 初始为 `pending`。测试随后直接把这个 pending Frontier 传给 `WorkflowWorker.execute_frontier()`。

`execute_frontier()` 的正式契约是消费已经由 Durable Frontier Claim 入口激活并绑定当前 Worker ownership 的 Frontier。其 heartbeat 会先执行带 ownership/status/attempt fencing 的 lease renewal；pending Frontier 没有当前 Worker ownership，因此 renewal 失败并取消当前 Runtime task。随后 finally 只能看到 Execution 仍为 running，无法进入正常 Runtime terminalization。

这不是 Execution terminal 状态机缺失。正常链路为：

`Delegation Claim → WorkflowExecution running + Frontier running/owned → WorkflowRuntime.execute → WorkflowExecution completed → Delegation completion`

### 修复

B2 验收测试改为通过正式 `_claim_pending_delegation_frontier()` 激活 pending Delegation Frontier 后再调用 `execute_frontier()`；若后台 Worker 已取得 ownership，则等待 durable terminal fact，不强制测试进程成为 owner。

同时保留并验证：Execution、Frontier、Delegation 三者必须最终 completed，Frontier ownership 必须释放。

## 2. B6 Provider actual invocation chain

### 现象

B6 多 Worker Real API 曾出现 `Mock provider HTTP 503`，随后 Delegation failed。

### 根因

测试 Fixture 先通过真实 HTTP 创建 pending Delegation，之后才在 PostgreSQL 中补齐 Target Agent Version 的 Mock Model Profile。真实后台 Worker 与测试 Worker 都是合法消费者，可能在 Profile 装配前先 Claim Delegation。此时 Bridge/Runtime 的 Provider 依赖尚未完整，失败属于测试 Fixture 发布顺序错误，而不是多 Worker Claim 语义要求失败。

### 正式 Provider 调用链核对

当前生产链路保持唯一实现：

`AgentVersion.model_profile_id`
→ `ModelProfile.provider_id`
→ `ModelProvider(provider_type="mock")`
→ `RuntimeModelGovernanceService.resolve()`
→ `ModelGateway.generate()`
→ `MockModelProvider.complete()`

`RuntimeModelGovernanceService` 根据 organization-scoped routing candidate 解析 Profile/Provider；`ModelGateway` 根据持久化 Provider 类型选择技术 Provider；显式绑定 Model Profile 时不会把真实 Provider 失败降级为无治理的本地 mock。

### 修复

Real API Fixture 改为：

1. 创建并发布 Target Agent；
2. 在创建 Delegation 前提交独立 Mock Provider/Profile；
3. 将 `AgentVersion.model_profile_id` 指向该 Profile；
4. 再创建 Delegation，使 `AgentDelegationService.create()` 从 Target Agent Version 固化同一个 `model_profile_id`；
5. B6 多 Worker 只竞争 Runtime 依赖已经完整的 pending Delegation。

B3 failure fixture 同样在 Delegation 可见前绑定 `mock-http-503`，因此 503 只用于显式失败契约，不再依赖“先 Claim、后补 Provider”产生偶发失败。

## 3. 不做的修改

- 不放宽 `Delegation.status == running` 的 Runtime Bridge Contract。
- 不把 `failed` 视为 B6 的成功结果。
- 不增加第二套 Worker Runtime 或 Provider 实现。
- 不修改多 Worker 合法竞争语义。
- 不在测试 Gate 中自动启动、停止或重启 API、Worker、Scheduler、PostgreSQL、Redis。
