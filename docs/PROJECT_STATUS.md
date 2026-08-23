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

当前 Real API 场景覆盖 governed Profile + connectivity failure + identity/secret boundary；尚未宣称真实外部 Provider 成功调用路径已验收。

本轮没有新增数据库表/字段，因此不需要 Migration。

## 当前验证状态

开发者本轮实际执行并反馈：

```text
2.3-C/D targeted unit tests: 28 passed
Backend default regression: 344 passed, 33 deselected
Real API Gate: blocked during bootstrap before test execution
```

Real API 阻塞原因已经定位并修复：`00_bootstrap_real_api.py` 原先在创建 Workflow/Execution retry/circuit fixtures 后才创建 Organization，随着 Runtime execution 强制要求 active Organization membership，fixture run 从预期的 `404` 变成 `403 当前用户没有有效的 Organization membership`。修复为先创建 Organization，再创建全部需要运行的 Workflow fixtures；同时不再复用可能缺少当前 tenant membership 的历史 workflow，而是创建本次 bootstrap 专用 executable fixture。

上述 Real API 本轮结果仍不得标记为 Passed；必须由开发者重新执行 Real API Gate 验证修复。

Migration/head verification：本轮反馈未提供执行结果，保持 Pending。

## 下一执行任务

**2.3-E Governed fallback success path + deterministic multi-provider acceptance**：先完成本轮 Real API Gate 重跑并确认 bootstrap 修复；随后补充真实可控 Provider adapter/fixture（不得以 Mock Provider 伪造 governed success），验证 candidate 顺序、bounded fallback、成功 outcome usage identity 与 fallback attempt trace；随后形成 Phase 2.3 acceptance gate。

## 开发纪律

- 远端 `main` 是唯一开发基线；不创建功能分支。
- 未实际执行的测试不得记录为 Passed。
- Runtime 数据继续使用数据库；JSON/JSONL 仅用于版本化 evaluation dataset/result/baseline。
- 新业务代码不得硬编码具体模型名称。
- Secret 不进入 Git、数据库明文、报告或 trace/audit。
- 代码与 Phase/Acceptance/Error/Status 必须保持可追溯。
