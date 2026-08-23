# Phase 2.3 — Model Provider Governance

> 状态：**2.3-A / 2.3-B / 2.3-C / 2.3-D / 2.3-E 已实现；2.3-E Real API acceptance 已通过；2.3-F Fallback Policy Enforcement 已实现，待本地验证。**

Phase 2.2 已正式关闭。Phase 2.3 在现有 Provider/Profile foundation 之上建立独立、可测试的 Provider Governance Runtime 能力。

## 2.3-A Provider Governance Contract — 已实现

- `explicit_profile` / `organization_default` routing strategy；
- fallback eligible reasons：connectivity / timeout / rate limit / provider 5xx；
- bounded fallback attempts，最大 2，默认 2；
- model type / capability / provider allowlist constraints；
- cost units + pricing source + pricing version；
- usage identity：organization/provider/profile/model_type/request/trace/outcome；
- Secret 不进入 usage/audit identity。

## 2.3-B Backend Domain + API Contract — 已实现

新增：`POST /api/v1/model-providers/routing/resolve`

- 仅 active organization member 可调用；
- 从 PostgreSQL 实际读取 Provider/Profile；
- 强制 organization scope、enabled、model type、capability 与 provider allowlist；
- `explicit_profile` 只返回指定 Profile；
- `organization_default` 只返回 default Profile，并使用 deterministic ordering；
- Response 不返回 endpoint、credential_ref 等连接敏感信息。

本任务没有新增数据库表/字段，因此不需要 Migration。

## 2.3-C Runtime Governance Invocation Service + WorkflowRuntime 接入 — 已实现

Runtime 主链路：

1. 读取已发布 `AgentVersion.model_profile_id`；
2. 有 `model_profile_id` 时使用 `explicit_profile`；
3. 无 `model_profile_id` 时使用 `organization_default`；
4. organization scope 从 Workflow execution tenant 对应的 active Organization 获取；
5. 通过 `RuntimeModelGovernanceService` 解析真实 PostgreSQL Provider/Profile；
6. 调用 `ModelGateway` 时显式传入 governed profile/provider；
7. fallback 仅接受 2.3-A 定义的 failure semantics；
8. 不允许静默 Mock fallback。

## 2.3-D Runtime Usage / Trace Identity — 已实现基础能力

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

开发者实际执行：

```text
Targeted runtime governance tests: 30 passed
Backend default regression: 348 passed, 34 deselected
Alembic upgrade head: passed
Tenant Safe Real API Gate: 34 passed
```

因此 2.3-E Real API acceptance 已关闭。

## 2.3-F Fallback Policy Enforcement — 已实现，待本地验证

此前 `FallbackPolicy` 已定义 `enabled`、`max_attempts`、`eligible_reasons`，但 Runtime invocation 实际执行只根据异常类型决定是否继续 fallback，导致 Contract 与 Runtime policy 存在脱节。

`dd037f8` 已修复：

- `max_attempts` 上限固定为 2；
- Runtime 可显式接收 `FallbackPolicy`；
- `enabled=false` 时失败立即返回，不进行 fallback；
- 只有 `eligible_reasons` 中的失败原因允许继续尝试；
- 调用方不能通过 `max_attempts` 绕过 policy 上限；
- 新增对应 unit tests，覆盖上限、eligible reasons 与 attempt limit。

该提交尚未由开发者本地执行，因此当前不能标记 2.3-F Passed。

## 下一执行任务

**2.3-F Acceptance Gate**：

```powershell
cd backend
uv run pytest -q tests/unit/test_model_provider_governance_contract.py tests/api_contract/test_api_model_provider_governance.py tests/unit/test_runtime_model_governance.py tests/unit/test_workflow_runtime.py
uv run pytest -q
uv run alembic upgrade head
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

全部通过后，进入 **2.3-G Cost / Usage Accounting**。若需要新增 usage/pricing 持久化结构，必须先新增 Alembic Migration，再实现依赖该结构的业务代码。
