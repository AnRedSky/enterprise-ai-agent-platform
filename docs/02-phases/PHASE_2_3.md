# Phase 2.3 — Model Provider Governance

> 状态：**2.3-A / 2.3-B / 2.3-C / 2.3-D / 2.3-E / 2.3-F / 2.3-G 已实现并完成对应本地验收；Phase 2.3 已正式关闭。**

Phase 2.2 已正式关闭。Phase 2.3 在现有 Provider/Profile foundation 之上建立独立、可测试、可追溯的 Provider Governance Runtime 能力。

## 2.3-A Provider Governance Contract — 已实现并验收

- `explicit_profile` / `organization_default` routing strategy；
- fallback eligible reasons：connectivity / timeout / rate limit / provider 5xx；
- bounded fallback attempts，最大 2，默认 2；
- model type / capability / provider allowlist constraints；
- cost units + pricing source + pricing version；
- usage identity：organization/provider/profile/model_type/request/trace/outcome；
- Secret 不进入 usage/audit identity。

## 2.3-B Backend Domain + API Contract — 已实现并验收

新增：`POST /api/v1/model-providers/routing/resolve`

- 仅 active organization member 可调用；
- 从 PostgreSQL 实际读取 Provider/Profile；
- 强制 organization scope、enabled、model type、capability 与 provider allowlist；
- `explicit_profile` 只返回指定 Profile；
- `organization_default` 只返回 default Profile，并使用 deterministic ordering；
- Response 不返回 endpoint、credential_ref 等连接敏感信息。

本任务没有新增数据库表/字段，因此不需要 Migration。

## 2.3-C Runtime Governance Invocation Service + WorkflowRuntime 接入 — 已实现并验收

Runtime 主链路：

1. 读取已发布 `AgentVersion.model_profile_id`；
2. 有 `model_profile_id` 时使用 `explicit_profile`；
3. 无 `model_profile_id` 时使用 `organization_default`；
4. organization scope 从 Workflow execution tenant 对应的 active Organization 获取；
5. 通过 `RuntimeModelGovernanceService` 解析真实 PostgreSQL Provider/Profile；
6. 调用 `ModelGateway` 时显式传入 governed profile/provider；
7. fallback 仅接受 2.3-A 定义的 failure semantics；
8. 不允许静默 Mock fallback。

## 2.3-D Runtime Usage / Trace Identity — 已实现并验收

已实现：

- 每次 governed provider attempt 生成独立 `request_id`；
- trace identity 写入 `organization_id/provider_id/profile_id/model_type/request_id/trace_id/outcome`；
- fallback failure 额外记录 `fallback_reason`；
- provider 成功时可记录 prompt/completion/total token usage；
- identity 记录通过 Workflow Trace 落库，不写入 endpoint/credential_ref；
- Runtime governance attempt callback 将每次 provider attempt 暴露给 Runtime trace。

## 2.3-E Governed fallback success + deterministic multi-provider — 已验收

Real API 场景覆盖：

- 进程内真实 HTTP OpenAI-compatible fixture server；
- Backend 通过真实 `OpenAICompatibleProvider` HTTP 调用 fixture，不使用 `MockProvider` 伪造 governed success；
- 第一候选返回 `503`，验证 `provider_5xx` fallback eligibility；
- 第二候选返回 `200` + usage，验证 bounded fallback success；
- 验证 deterministic candidate ordering、独立 request identity、统一 execution trace identity、usage identity 与 Secret boundary。

## 2.3-F Fallback Policy Enforcement — 已验收

`dd037f8` 已将 Contract 中的 fallback policy 提升为 Runtime 强制规则：

- `max_attempts` 上限固定为 2；
- Runtime 可显式接收 `FallbackPolicy`；
- `enabled=false` 时失败立即返回，不进行 fallback；
- 只有 `eligible_reasons` 中的失败原因允许继续尝试；
- 调用方不能通过 `max_attempts` 绕过 policy 上限；
- 补充 HTTPX write/pool timeout 分类与 provider timeout fallback 测试。

## 2.3-G Cost / Usage Accounting — 已验收

本任务把已有 Contract 的 cost/usage 定义真正落到 PostgreSQL，而不是继续只记录在 trace JSON 中。

### 持久化

新增 `model_usage_records`，每一次 governed provider attempt 一条记录：

- organization / tenant / execution / workflow / node scope；
- provider / profile / model identity；
- request / trace / outcome / fallback reason；
- prompt / completion / total tokens；
- request / input token / output token usage units；
- pricing source / version；
- input/output/request/total cost。

### Pricing contract

Model Profile 的 `parameters.pricing` 支持：

```json
{
  "pricing_source": "provider_pricing",
  "pricing_version": "fixture-v1",
  "input_token_per_1k": 0.002,
  "output_token_per_1k": 0.004,
  "request": 0.001
}
```

token cost 按每 1,000 tokens 计算；request cost 按 provider attempt 计算。没有配置 pricing 时仍记录 usage/request identity，但成本为 0，并保留 `pricing_version=unconfigured`，禁止伪造计费结果。

### Query API

新增：`GET /api/v1/usage/model`

- 必须属于 active organization member；
- 支持 `organization_id`、可选 `execution_id`、offset/limit；
- 返回 durable usage records 与 organization scoped `total_cost`；
- 不返回 endpoint / credential_ref / Secret。

### 本地 Acceptance 证据

开发者在最新 `main`（`14fd450`）实际执行：

```text
2.3-G targeted tests: 40 passed
Backend default regression: 358 passed, 35 deselected
Alembic upgrade heads: passed
Alembic current: 0023_model_usage_accounting (head), 0027_retrieval_evaluation_vector_space (head)
Tenant Safe Real API Gate: 35 passed
```

因此 2.3-G 已通过本地 Acceptance，并与 2.3-A 至 2.3-F 一起关闭 Phase 2.3。

## Phase 2.3 关闭结论

Provider routing、governed fallback、fallback policy、usage identity、真实 PostgreSQL usage persistence、pricing/cost calculation 与 organization scoped usage query 已完成并通过本地 Gate。当前没有新的已确认 Provider Governance 开发缺口。

下一阶段只能先完成 Phase 2.4 Durable Scheduler 的产品 / Contract 确认，再进入代码开发。
