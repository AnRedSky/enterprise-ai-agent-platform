# Phase 2.3 — Model Provider Governance

> 状态：**2.3-A / 2.3-B 已实现；2.3-C Runtime Governance Invocation Service 已实现基础服务，WorkflowRuntime 主链路接入待继续完成。**

Phase 2.2 已正式关闭。Phase 2.3 在现有 Provider/Profile foundation 之上建立独立、可测试的 Provider Governance Runtime 能力。

## 2.3-A 首批 Contract

### 1. Provider routing strategy

- `explicit_profile`：Runtime 必须明确提供 `model_profile_id`，否则不得隐式挑选 Provider。
- `organization_default`：仅显式选择该策略时，按 Organization scope、model type、enabled、capability 与 provider allowlist 过滤 default Profile，并以稳定排序产生候选。
- 禁止按具体 provider/model 名称硬编码路由。

### 2. Fallback eligibility / failure semantics

Fallback 首版仅允许 connectivity、timeout、rate limit、provider 5xx；认证、参数校验、能力不匹配、业务 4xx 等错误不得自动 fallback。最大尝试次数有上限，默认 `2`。

### 3. Model whitelist / capability constraints

候选必须同时满足 organization scope、enabled、requested `model_type`、required capabilities 与 optional provider allowlist。

### 4. Cost accounting

成本建立在明确 usage unit 与 versioned pricing source 上，支持 input token、output token、embedding token、request；pricing source 与 `pricing_version` 必须显式标识。

### 5. Usage accounting / audit identity

每次模型调用的 usage identity 至少包含 `organization_id + provider_id + profile_id + model_type + request_id + trace_id + outcome`。Secret、credential、API key 不属于 usage/audit identity。

## 2.3-B Backend Domain + API Contract — 已实现

新增：`POST /api/v1/model-providers/routing/resolve`

- 仅 active organization member 可调用；
- 从 PostgreSQL 实际读取 Provider/Profile；
- 强制 organization scope、enabled、model type、capability 与 provider allowlist；
- `explicit_profile` 只返回指定 Profile；
- `organization_default` 只返回 default Profile，并使用 deterministic ordering；
- Response 不返回 endpoint、credential_ref 等连接敏感信息。

本任务没有新增数据库表/字段，因此不需要 Migration。

## 2.3-C Runtime Governance Invocation Service — 基础实现

新增：

- `backend/app/services/runtime_model_governance.py`
- `backend/tests/unit/test_runtime_model_governance.py`

当前服务已经完成：

1. 调用 2.3-B routing resolver 获取候选；
2. 从 PostgreSQL 重新加载真实 ModelProfile/ModelProvider；
3. 以 `model_profile` + `model_provider` 显式调用 `ModelGateway`；
4. 只对 connectivity / timeout / rate limit / provider 5xx 执行候选切换；
5. 非治理允许错误直接失败；
6. governed invocation 不允许退回 Mock Provider 伪造成功。

### 尚未完成

`WorkflowRuntime.execute_node()` 尚未接入 `RuntimeModelGovernanceService`。因此当前 2.3-C 仍不能标记为 Runtime Integration Passed。

## 当前验证状态

开发者上一轮已经实际反馈：

```text
2.3-A targeted unit + API Contract: 11 passed
Backend regression: 334 passed, 32 deselected
Real API Gate: 32 passed
Frontend regression: 18 files / 75 tests passed + production build passed
```

这些结果对应 2.3-A/B 基线；本次新增 2.3-C 代码尚未由开发者本地执行，因此新增验证保持 Pending。

## 下一执行任务

**2.3-C WorkflowRuntime 主链路接入**：把 `RuntimeModelGovernanceService` 接入 `WorkflowRuntime.execute_node()`，让已发布 AgentVersion 的 `model_profile_id` 真正驱动 candidate → provider invocation；无 `model_profile_id` 时按明确 routing strategy 处理，不允许静默 Mock fallback。

完成后新增 Real API Runtime governance 场景，验证真实 PostgreSQL Provider/Profile、fallback failure semantics、request/trace identity 与实际 Provider invocation。

若后续引入持久化 routing policy / pricing / usage record，必须先新增 Alembic Migration，再实现依赖该结构的业务代码。

## Gate 纪律

```powershell
cd backend
uv run pytest -q tests/unit/test_model_provider_governance_contract.py tests/api_contract/test_api_model_provider_governance.py tests/unit/test_runtime_model_governance.py
uv run pytest -q
uv run alembic upgrade head
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

上述命令必须由开发者本地实际执行；未执行的结果不得标记为 Passed。
