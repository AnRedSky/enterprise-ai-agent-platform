# Phase 2.8 Worker / Delegation 多实例真实 Provider 能力缺口

## 1. 问题

既有 B6 多 Worker Real API Gate 可以验证多个 Worker 竞争 Delegation Durable Frontier，但测试 Fixture 为了隔离外部模型 Provider，主动创建并绑定 Mock Provider/Profile。

因此 Gate 的“Real API”含义是：真实 Backend HTTP + PostgreSQL + Worker Runtime；并不等价于真实外部 Model Provider HTTP。

## 2. 根因

问题不在 Worker Claim、Lease、Delegation Runtime Bridge 或 Model Gateway 的生产实现。

生产代码已经存在完整路径：

```text
Delegation.model_profile_id
→ AgentDelegationRuntimeBridge
→ execute_claimed_execution
→ WorkflowRuntime.execute_node
→ RuntimeModelGovernanceService.invoke
→ ModelProviderService.resolve_routing
→ ModelGateway.generate
→ OpenAICompatibleProvider
```

B6 Gate 的边界是测试隔离策略造成的能力证据缺失，而不是生产功能缺失。

## 3. 为什么不能继续用 Mock 修复

如果继续只绑定 Mock Provider，会掩盖以下生产边界：

- Worker 子进程是否能够读取真实 Provider endpoint；
- credential_ref 是否在独立 Worker 进程中正确解析；
- Provider/Profile tenant 与 organization routing 是否保持一致；
- 两个 Worker 是否都能经过同一 Model Governance Contract 调用真实 Provider；
- 真实 Provider HTTP failure 是否沿 Worker Runtime / Delegation lifecycle 正确收敛。

因此不能通过增加 Mock 行为或复制 Provider 实现解决。

## 4. 修复策略

新增独立 Real Provider Acceptance：

- 测试动态创建真实 Provider/Profile；
- endpoint、model、credential ref 从未提交环境读取；
- 两个独立 Worker 竞争多个 Delegation；
- 禁止后台 Worker/Scheduler 抢占测试 Fixture；
- PostgreSQL 验证 Delegation、Execution、Frontier 最终事实；
- 单独 Gate 编排，保持与 B6 Mock Provider Gate 的职责分离。

## 5. 配置安全

真实 API key 不允许写入测试代码、Provider metadata 或 Git。推荐：

```text
DELEGATION_REAL_PROVIDER_API_KEY_ENV=MY_REAL_PROVIDER_API_KEY
```

数据库只保存 `credential_ref=MY_REAL_PROVIDER_API_KEY`，实际 Secret 留在未提交环境变量中。

## 6. 关闭条件

必须由开发者本地实际执行 `07_delegation_multi_worker_real_provider_gate.ps1` 并取得完整通过结果后，才能将该缺口标记为已关闭。
