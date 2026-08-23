# Project Status

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**进行中**。
- 2.3-A Provider Governance Contract：**已实现**。
- 2.3-B Backend Domain + API Contract：**已实现**。
- 2.3-C Runtime Governance Invocation Service：**已实现并接入 WorkflowRuntime 主链路，待本地验证**。

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

本轮没有新增数据库表/字段，因此不需要 Migration。

同时新增 Real API 场景，验证：

- 已发布 AgentVersion 的 `model_profile_id` 能进入 Runtime governed invocation；
- 无法连接 governed Provider 时按失败语义结束，不切换到 Mock success；
- trace/audit 不泄漏 credential_ref。

### 当前尚未宣称完成的部分

2.3-A 中定义的 usage identity 维度已经作为 Contract 存在，但本轮没有虚构“usage persistence 已完成”的状态；需要下一步把 provider/profile/model_type/request/trace/outcome 接入实际 runtime usage/trace 记录后，再进行验收。

## 当前验证状态

本轮代码已提交远端 `main`，但本次会话无法直接执行开发者本地 uv/PostgreSQL 环境，因此不得把以下项目标记为 Passed：

```text
2.3-A targeted unit test: developer previously executed 11 passed
2.3-B API Contract test: developer previously included in 334-test regression
2.3-C targeted unit tests: Pending local execution after WorkflowRuntime integration
Backend default regression after 2.3-C: Pending
Migration/head verification after 2.3-C: Pending (no migration expected)
Real API after 2.3-C: Pending local execution
Runtime governed invocation integration: Implemented, validation Pending
```

## 下一执行任务

**2.3-D Runtime Usage / Trace Identity**：把 `organization/provider/profile/model_type/request_id/trace_id/outcome` 按 2.3-A `UsageIdentity` Contract 接入实际 runtime usage/trace 记录，并新增 Real API 验证；继续保持 Secret 不进入 usage/audit/trace。

随后再推进 governed fallback 的成功路径与多 Provider deterministic candidate 顺序验证。

## 开发纪律

- 远端 `main` 是唯一开发基线；不创建功能分支。
- 未实际执行的测试不得记录为 Passed。
- Runtime 数据继续使用数据库；JSON/JSONL 仅用于版本化 evaluation dataset/result/baseline。
- 新业务代码不得硬编码具体模型名称。
- Secret 不进入 Git、数据库明文、报告或 trace/audit。
- 代码与 Phase/Acceptance/Error/Status 必须保持可追溯。
