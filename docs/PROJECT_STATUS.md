# Project Status

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**进行中**。
- 2.3-A Provider Governance Contract：**已实现并进入运行时强制执行**。
- 2.3-B Backend Domain + API Contract：**已实现**。
- 2.3-C Runtime Governance Invocation：**已实现并接入 WorkflowRuntime**。
- 2.3-D Runtime Usage / Trace Identity：**已实现基础能力**。
- 2.3-E Governed fallback success + deterministic multi-provider：**已通过开发者本地 Real API Gate**。
- 2.3-F Fallback Policy Enforcement：**已通过开发者本地 targeted regression、Backend regression、Migration 与 Tenant Safe Real API Gate**。
- 2.3-G Cost / Usage Accounting：**已实现第一版持久化与查询能力，待本地 Gate 验证**。

## 本轮实际验收证据

开发者在最新 `main`（`843e19d`）实际执行并反馈：

```text
Targeted runtime governance tests: 33 passed
Backend default regression: 351 passed, 34 deselected
Alembic upgrade head: passed
Tenant Safe Real API Gate: 34 passed
```

因此 2.3-F Fallback Policy Enforcement 的本地 acceptance blocker 已关闭。该结果是在 `dd037f8` 的 Runtime policy enforcement 后实际执行的，不能再把 2.3-F 标记为“待验证”。

此前 `fallback_reason=connectivity` / actual `timeout` 不一致已修复，并进一步补齐 HTTPX write/pool timeout 分类；随后 Runtime 已强制执行 `FallbackPolicy.enabled`、`eligible_reasons` 与最大 attempts=2。

## 当前 Runtime Governance 实现

Runtime 主链路现在：

1. 读取已发布 `AgentVersion.model_profile_id`；
2. 有 `model_profile_id` 时使用 `explicit_profile`；
3. 无 `model_profile_id` 时使用 `organization_default`；
4. organization scope 从 Workflow execution tenant 对应的 active Organization 获取；
5. 通过 `RuntimeModelGovernanceService` 解析真实 PostgreSQL Provider/Profile；
6. 调用 `ModelGateway` 时显式传入 governed profile/provider；
7. fallback 只接受治理 Contract 定义的 connectivity / timeout / rate limit / provider 5xx；
8. fallback attempt 数量受 `FallbackPolicy.max_attempts` 上限约束，当前最大值为 2；
9. `FallbackPolicy.enabled` 与 `eligible_reasons` 实际控制 Runtime fallback；
10. 不允许静默 Mock fallback；
11. 每次 provider attempt 生成独立 `request_id`，并通过 Workflow Trace 记录 usage identity；
12. `model.invocation` trace 与 Model Usage Accounting 在同一数据库事务中持久化，避免 trace 与 usage 记录脱节。

## 当前执行任务

**2.3-G Cost / Usage Accounting**：将 2.3-A 中已定义的 cost units / pricing source / pricing version 与 2.3-D usage identity 提升为真实 PostgreSQL 持久化和查询能力。

已提交本轮实现：

- 新增 `model_usage_records` 持久化表及 `0023_model_usage_accounting` migration；
- 每次 governed provider attempt 生成一条 durable usage record，包括成功、失败与 fallback attempt；
- 支持 request / input token / output token usage units；
- 支持 Model Profile `parameters.pricing` 中配置 `pricing_source`、`pricing_version`、`input_token_per_1k`、`output_token_per_1k`、`request`；
- 支持 deterministic token/request cost calculation；未配置 pricing 时成本为 0，但 usage identity 与 request unit 仍真实落库；
- 新增 tenant/organization scoped `GET /api/v1/usage/model` 查询；
- 新增 targeted unit、API contract 与 Real API accounting tests。

## 下一步

1. 开发者本地执行 2.3-G targeted tests；
2. 执行 Backend default regression；
3. 执行 `uv run alembic upgrade head`；
4. 执行 Tenant Safe Real API Gate，验证真实 PostgreSQL usage record 与成本计算；
5. 全部通过后关闭 2.3-G acceptance；
6. 再评估 Phase 2.3 是否还有 Provider Governance 范围内的剩余能力；若无，则准备 Phase 2.3 closeout，而不是提前进入候选 Phase 2.4。

## 开发纪律

- 远端 `main` 是唯一开发基线；不创建功能分支。
- 未实际执行的测试不得记录为 Passed。
- Runtime 数据继续使用 PostgreSQL；JSON/JSONL 仅用于版本化 evaluation dataset/result/baseline。
- 新业务代码不得硬编码具体模型名称。
- Secret 不进入 Git、数据库明文、报告或 trace/audit。
- 代码与 Phase/Acceptance/Error/Status 必须保持可追溯。
