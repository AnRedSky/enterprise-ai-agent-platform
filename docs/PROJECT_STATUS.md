# Project Status

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**进行中**。
- 2.3-A Provider Governance Contract：**已实现**。
- 2.3-B Backend Domain + API Contract：**已实现**。
- 2.3-C Runtime Governance Invocation Service：**已实现并接入 WorkflowRuntime 主链路**。
- 2.3-D Runtime Usage / Trace Identity：**已实现基础 trace identity，待完整 acceptance**。
- 2.3-E Governed fallback success path：**已补充真实 HTTP Provider fixture 测试，待本地 Real API 验证**。

## Phase 2.2 最终验证证据

开发者实际执行并反馈：

```text
Backend Real API Gate: 32 passed
Frontend Regression Gate: 18 test files / 75 tests passed; vue-tsc + Vite build passed
Model Provider/Profile Browser E2E: 2 passed
```

因此 **E-4 Passed / Phase 2.2 Closed**。不得继续向 2.2 塞入新的 Provider routing / fallback / cost / usage 功能。

## Phase 2.3 当前实现

### 2.3-A Provider Governance Contract

已提交可执行 Contract：

- `explicit_profile` / `organization_default` routing strategy；
- fallback eligible reasons：connectivity / timeout / rate limit / provider 5xx；
- bounded fallback attempts，默认 2；
- model type / capability / provider allowlist constraints；
- cost units + pricing source + pricing version；
- usage identity：organization/provider/profile/model_type/request/trace/outcome；
- Secret 不进入 usage/audit identity。

### 2.3-B Backend Domain + API Contract

已新增真实数据库 Provider/Profile 候选解析接口：

`POST /api/v1/model-providers/routing/resolve`

该接口使用 PostgreSQL Provider/Profile 数据，强制 Organization membership scope，并不返回 endpoint、credential_ref 等敏感连接信息。

### 2.3-C Runtime Governance Invocation Service + WorkflowRuntime 接入

已实现：

- `backend/app/services/runtime_model_governance.py`
- `backend/app/runtime/workflow_runtime.py`
- `backend/tests/unit/test_runtime_model_governance.py`
- `backend/tests/unit/test_workflow_runtime.py`
- `backend/tests/api_real/test_runtime_model_governance_api.py`

Runtime 主链路现在：

1. 读取已发布 `AgentVersion.model_profile_id`；
2. 有 `model_profile_id` 时使用 `explicit_profile`；
3. 无 `model_profile_id` 时使用 `organization_default`；
4. organization scope 从 Workflow execution tenant 对应的 active Organization 获取；
5. 通过 `RuntimeModelGovernanceService` 解析真实 PostgreSQL Provider/Profile；
6. 调用 `ModelGateway` 时显式传入 governed profile/provider；
7. fallback 仅接受 2.3-A 定义的 connectivity / timeout / rate limit / provider 5xx；
8. 不允许静默 Mock fallback。

### 2.3-D Runtime Usage / Trace Identity

已实现：

- 每次 governed provider attempt 生成独立 `request_id`；
- trace identity 写入 `organization_id/provider_id/profile_id/model_type/request_id/trace_id/outcome`；
- fallback failure 额外记录 `fallback_reason`；
- provider 成功时可记录 prompt/completion/total token usage；
- identity 记录通过 Workflow Trace 落库，不写入 endpoint/credential_ref；
- `RuntimeModelGovernanceService` 通过 attempt callback 将每次 provider attempt 暴露给 Runtime governance trace。

当前 Real API 场景覆盖 governed Profile + connectivity/timeout failure + identity/secret boundary；尚未宣称真实外部 Provider 成功调用路径已验收。

### 2.3-E Governed fallback success path + deterministic multi-provider acceptance

已新增 Real API 测试：

- `backend/tests/api_real/test_runtime_model_governance_api.py`
- 本地测试 HTTP server 使用真实 `OpenAICompatibleProvider` 协议，不使用 `MockProvider` 伪造 governed success；
- 第一候选真实 HTTP 返回 `503`，验证 `provider_5xx` fallback eligibility；
- 第二候选返回 `200`，验证 bounded fallback success；
- 验证 candidate deterministic ordering、独立 request_id、同一 execution trace_id、成功 usage identity 与 Secret boundary。

## 当前验证状态

开发者本轮实际执行并反馈：

```text
Backend default regression: 346 passed, 34 deselected
Real API Gate: 33 passed, 1 failed
Failure: test_runtime_uses_published_model_profile_and_records_usage_identity_without_mock_fallback
Expected fallback_reason=connectivity; actual fallback_reason=timeout
```

此前 Real API bootstrap 的 tenant/membership 与 governed mock fixture 边界已完成修复。当前阻塞点已收敛为测试断言与 timeout 分类契约不一致；提交 `43f9e683d00d936db94f249b4e587654e9517914` 已将断言调整为 `timeout`。该提交之后尚未由开发者重新执行完整 Real API Gate，因此不得标记为 Passed。

对应工程错误已记录到 `docs/04-errors/2026-08-23-phase-2-3-real-api-provider-timeout-fallback-reason.md`。

## 下一执行任务

**2.3-E Acceptance Gate**：拉取最新 `main`（至少包含 `43f9e683` 及其后的错误记录提交），重新执行 Tenant Safe Real API Gate；若失败，按实际失败继续修复并记录 `docs/04-errors/`；若通过，再执行完整 Backend regression + Migration/head + Real API 三层 Backend Gate，最终更新 Phase 2.3 Acceptance 记录并进入下一项任务。

## 开发纪律

- 远端 `main` 是唯一开发基线；不创建功能分支。
- 未实际执行的测试不得记录为 Passed。
- Runtime 数据继续使用数据库；JSON/JSONL 仅用于版本化 evaluation dataset/result/baseline。
- 新业务代码不得硬编码具体模型名称。
- Secret 不进入 Git、数据库明文、报告或 trace/audit。
- 代码与 Phase/Acceptance/Error/Status 必须保持可追溯。
