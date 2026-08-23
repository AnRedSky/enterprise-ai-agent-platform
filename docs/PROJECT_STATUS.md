# Project Status

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**已正式关闭**。
- 2.3-A Provider Governance Contract：**已实现并进入运行时强制执行**。
- 2.3-B Backend Domain + API Contract：**已实现**。
- 2.3-C Runtime Governance Invocation：**已实现并接入 WorkflowRuntime**。
- 2.3-D Runtime Usage / Trace Identity：**已实现**。
- 2.3-E Governed fallback success + deterministic multi-provider：**已通过开发者本地 Real API Gate**。
- 2.3-F Fallback Policy Enforcement：**已通过开发者本地 targeted regression、Backend regression、Migration 与 Tenant Safe Real API Gate**。
- 2.3-G Cost / Usage Accounting：**已通过开发者本地 targeted regression、Backend regression、Migration 与 Tenant Safe Real API Gate，Phase 2.3 已关闭**。

## 本轮实际验收证据

开发者在最新 `main`（`14fd450`）实际执行并反馈：

```text
2.3-G targeted tests: 40 passed
Backend default regression: 358 passed, 35 deselected
Alembic upgrade heads: passed
Alembic current: 0023_model_usage_accounting (head), 0027_retrieval_evaluation_vector_space (head)
Tenant Safe Real API Gate: 35 passed
```

因此 2.3-G 的本地 acceptance blocker 已关闭。上述结果均来自开发者本地实际执行，不以 GitHub Actions 作为验收依据。

## Phase 2.3 交付结果

Runtime 主链路已形成完整的 Provider Governance：

1. 读取已发布 `AgentVersion.model_profile_id`；
2. 有 `model_profile_id` 时使用 `explicit_profile`；
3. 无 `model_profile_id` 时使用 `organization_default`；
4. organization scope 从 Workflow execution tenant 对应的 active Organization 获取；
5. 通过 `RuntimeModelGovernanceService` 解析真实 PostgreSQL Provider/Profile；
6. 调用 `ModelGateway` 时显式传入 governed profile/provider；
7. fallback 只接受治理 Contract 定义的 connectivity / timeout / rate limit / provider 5xx；
8. `FallbackPolicy.enabled`、`eligible_reasons` 与最大 attempts=2 实际控制 Runtime fallback；
9. 不允许静默 Mock fallback；
10. 每次 provider attempt 生成独立 `request_id`，并通过 Workflow Trace 记录 usage identity；
11. 每次 governed provider attempt 生成 durable `model_usage_records`；
12. usage identity、pricing source/version、token/request units 与成本均从真实 PostgreSQL 持久化数据查询；
13. `model.invocation` trace 与 Model Usage Accounting 在同一数据库事务中持久化，避免 trace 与 usage 记录脱节；
14. usage 查询严格按 active organization membership 做 tenant scope 校验；
15. endpoint、credential_ref、Token、Secret 不进入 usage/audit/trace。

## Phase 2.3 关闭结论

2.3-A 至 2.3-G 均已完成对应本地验收。当前 Provider Governance 范围内没有新的已确认开发缺口，因此 Phase 2.3 正式关闭，不继续扩张未经产品确认的 UI、E2E 或 Provider 能力。

## 下一阶段

候选下一阶段为 **Phase 2.4 Durable Scheduler**。当前只能进入需求 / Contract 确认，不直接把历史规划转成代码任务。正式进入开发前必须明确：

1. `next_run_at` 的计算与时区语义；
2. 多实例 scheduler lease / ownership 语义；
3. lease 过期、抢占与重复执行边界；
4. misfire policy 与可接受延迟；
5. 执行幂等键与重复触发语义；
6. paused / enabled / disabled 状态转换；
7. 调度状态与 WorkflowExecution 的审计、trace 关系；
8. PostgreSQL migration 与 Real API acceptance 场景。

在上述 Contract 未确认前，不以“Scheduler”技术名词自行扩大产品范围。

## 开发纪律

- 远端 `main` 是唯一开发基线；不创建功能分支。
- 未实际执行的测试不得记录为 Passed。
- Runtime 数据继续使用 PostgreSQL；JSON/JSONL 仅用于版本化 evaluation dataset/result/baseline。
- 新业务代码不得硬编码具体模型名称。
- Secret 不进入 Git、数据库明文、报告或 trace/audit。
- 代码、Phase、Acceptance、Error、Status 必须保持可追溯。
- 代码中的功能说明和注释统一使用中文；技术标识保持原文。
