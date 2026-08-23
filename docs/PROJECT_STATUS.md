# Project Status

## 当前阶段

- Repository: `AnRedSky/enterprise-ai-agent-platform`
- Branch: `main`
- Phase 2.2 Retrieval Production Quality：**已正式关闭**。
- Phase 2.3 Model Provider Governance：**进行中**。
- 2.3-A Provider Governance Contract：**已实现**。
- 2.3-B Backend Domain + API Contract：**已实现**。
- 2.3-C Runtime Governance Invocation Service：**已实现基础服务，WorkflowRuntime 主链路接入待本地验证后继续推进**。

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

### 2.3-C Runtime Governance Invocation Service

新增：

- `backend/app/services/runtime_model_governance.py`
- `backend/tests/unit/test_runtime_model_governance.py`

服务职责：

- 调用既有 routing resolver 获取治理候选；
- 将候选重新绑定到真实 PostgreSQL ModelProfile/ModelProvider；
- 调用 `ModelGateway` 时显式传入 profile/provider；
- fallback 仅接受 2.3-A 定义的 connectivity / timeout / rate limit / provider 5xx；
- 非治理允许错误直接失败；
- 不使用 Mock Provider 伪造 governed Provider 成功。

本轮没有新增数据库表/字段，因此不需要 Migration。

## 当前验证状态

本轮代码已提交远端 `main`，但新增 2.3-C 代码尚未由开发者本地 uv/PostgreSQL 环境执行，因此保持 Pending：

```text
2.3-A targeted unit test: developer previously executed 11 passed
2.3-B API Contract test: developer previously included in 334-test regression
Backend default regression after 2.3-C: Pending
Migration/head verification after 2.3-C: Pending
Real API after 2.3-C: Pending
Runtime governed invocation integration: Pending
```

## 下一执行任务

**2.3-C RuntimeWorkflow 主链路接入**：把 `RuntimeModelGovernanceService` 接入 `WorkflowRuntime.execute_node()`，让已发布 AgentVersion 的 `model_profile_id` 真正驱动 candidate → provider invocation；无 `model_profile_id` 时按明确的 organization routing strategy 处理，不允许静默 Mock fallback。

随后新增 Real API Runtime governance 场景，验证真实数据库 Provider/Profile、fallback failure semantics 与 usage/trace identity。

## 开发纪律

- 远端 `main` 是唯一开发基线；不创建功能分支。
- 未实际执行的测试不得记录为 Passed。
- Runtime 数据继续使用数据库；JSON/JSONL 仅用于版本化 evaluation dataset/result/baseline。
- 新业务代码不得硬编码具体模型名称。
- Secret 不进入 Git、数据库明文、报告或 trace/audit。
- 代码与 Phase/Acceptance/Error/Status 必须保持可追溯。
