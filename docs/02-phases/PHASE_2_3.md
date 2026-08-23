# Phase 2.3 — Model Provider Governance

> 状态：**2.3-A Contract 已实现；2.3-B Backend Domain/API Contract 已实现，等待开发者本地 Contract/Regression/Real API 验证。**

Phase 2.2 已正式关闭。Phase 2.3 不修改 2.2 Retrieval/Profile foundation，而是在其之上建立独立、可测试的 Provider Governance Contract。

## 2.3-A 首批 Contract

### 1. Provider routing strategy

- `explicit_profile`：默认策略。Runtime 必须明确提供 `model_profile_id`，否则不得隐式挑选 Provider。
- `organization_default`：仅在显式选择该策略时，按 Organization scope、model type、enabled、capability 与 provider allowlist 过滤 default Profile，并以稳定排序产生候选。
- 禁止按具体 provider/model 名称硬编码路由。

### 2. Fallback eligibility / failure semantics

Fallback 不是“任何异常都换 Provider”。首版允许的候选失败原因仅为 connectivity、timeout、rate limit、provider 5xx；认证、参数校验、能力不匹配、业务 4xx 等错误不得自动 fallback。首版最大尝试次数有上限，默认 `2`。

### 3. Model whitelist / capability constraints

路由候选必须同时满足 organization scope、enabled、requested `model_type`、required capabilities 与 optional provider allowlist。Whitelist 使用 Provider/Profile identity 与 capabilities 表达，不在业务代码中硬编码具体模型名称。

### 4. Cost accounting

成本必须建立在明确的 usage unit 与 versioned pricing source 上。首批 Contract 支持 input token、output token、embedding token、request。Pricing source 必须显式标识为 provider pricing 或 platform pricing，并带 `pricing_version`。

### 5. Usage accounting / audit identity

每次模型调用的 usage identity 至少包含 `organization_id + provider_id + profile_id + model_type + request_id + trace_id + outcome`。Secret、credential、API key 不属于 usage/audit identity。

## 2.3-B Backend Domain + API Contract — 已实现，待验证

新增 `POST /api/v1/model-providers/routing/resolve`：

- 仅 active organization member 可调用；
- 从 PostgreSQL 实际读取 Provider/Profile，而不是 JSON/fixture 数据；
- 强制 organization scope、enabled、model type、capability 与 provider allowlist；
- `explicit_profile` 只返回指定 Profile；未指定 Profile 不产生隐式候选；
- `organization_default` 只返回 default Profile，并使用 deterministic ordering；
- Response 只返回 routing identity 与 capability，不返回 endpoint credential_ref 等 Secret/连接敏感信息。

实现位于：

- `backend/app/services/model_provider.py`
- `backend/app/schemas/model_provider.py`
- `backend/app/api/model_providers.py`
- `backend/app/services/model_provider_governance_contract.py`

API Contract 测试新增：`backend/tests/api_contract/test_api_model_provider_governance.py`。

本任务没有新增数据库表/字段，因此**不需要 Migration**；Runtime 仍使用现有数据库 Provider/Profile 数据源。

## 当前验证状态

本轮代码由远端 main 原子提交，但本环境没有替代开发者本地 uv/PostgreSQL/真实 Provider 的验收结果。因此以下均保持 Pending，不写成 Passed：

```text
2.3-A targeted unit test: Pending developer execution
2.3-B API Contract test: Pending developer execution
Backend regression: Pending developer execution
Migration/head verification: Pending developer execution
Real API: Pending developer execution
```

## 下一任务

**2.3-C Runtime Routing Integration**：把 `routing/resolve` 的治理候选与现有 `SessionService.load_runtime()` / `ModelGateway` 连接起来，形成真实 Runtime candidate → provider invocation 链路；fallback 仍必须遵守 2.3-A failure semantics，不能退回 Mock 伪造成功。

若 2.3-C 需要持久化 routing policy / pricing / usage record，必须先新增 Alembic Migration，再实现依赖该结构的业务代码。

## Gate 纪律

```powershell
cd backend
uv run pytest -q tests/unit/test_model_provider_governance_contract.py tests/api_contract/test_api_model_provider_governance.py
uv run pytest -q
uv run alembic upgrade head
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

上述命令必须由开发者本地实际执行；未执行的结果不得标记为 Passed。
