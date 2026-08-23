# Phase 2.3 — Model Provider Governance

> 状态：**2.3-A Provider Governance Contract 已完成；Runtime routing / fallback / cost / usage 业务实现尚未开始。**

Phase 2.2 已正式关闭。Phase 2.3 不修改 2.2 Retrieval/Profile foundation，而是在其之上建立独立、可测试的 Provider Governance Contract。

## 2.3-A 首批 Contract

### 1. Provider routing strategy

- `explicit_profile`：默认策略。Runtime 必须明确提供 `model_profile_id`，否则不得隐式挑选 Provider。
- `organization_default`：仅在显式选择该策略时，按 Organization scope、model type、enabled、capability 与 provider allowlist 过滤 default Profile，并以稳定排序产生候选。
- 禁止按具体 provider/model 名称硬编码路由。

### 2. Fallback eligibility / failure semantics

Fallback 不是“任何异常都换 Provider”。首版允许的候选失败原因仅为：

- connectivity；
- timeout；
- rate limit；
- provider 5xx。

认证、参数校验、能力不匹配、业务 4xx 等错误不得自动 fallback。首版最大尝试次数有上限，默认 `2`。

### 3. Model whitelist / capability constraints

路由候选必须同时满足：

- organization scope；
- enabled；
- requested `model_type`；
- required capabilities；
- optional provider allowlist。

Whitelist 使用 Provider/Profile identity 与 capabilities 表达，不在业务代码中硬编码具体模型名称。

### 4. Cost accounting

成本必须建立在明确的 usage unit 与 versioned pricing source 上。首批 Contract 支持：

- input token；
- output token；
- embedding token；
- request。

Pricing source 必须显式标识为 provider pricing 或 platform pricing，并带 `pricing_version`。未获得真实 usage 时不得用隐式估算冒充真实成本。

### 5. Usage accounting / audit identity

每次模型调用的 usage identity 至少包含：

`organization_id + provider_id + profile_id + model_type + request_id + trace_id + outcome`

Secret、credential、API key 不属于 usage/audit identity。

## 当前代码交付

`backend/app/services/model_provider_governance_contract.py` 提供可执行 Contract 与 deterministic candidate selection；`backend/tests/unit/test_model_provider_governance_contract.py` 对 routing、fallback、capability/allowlist、cost pricing version、usage identity 建立单元断言。

本提交**不**把 Contract 当作已完成的 Runtime 功能。下一任务是 2.3-B：Backend Domain/API Contract，随后再按开发准则进入 Migration（若需要持久化策略）、Backend Tests、Real API、Frontend/Browser（按实际范围裁剪）。

## Gate 纪律

本阶段代码变更提交前必须由开发者本地实际执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_model_provider_governance_contract.py
```

然后再执行 Backend default regression、migration/head verification 与 Real API Gate。未实际执行的结果不得记录为 Passed。
