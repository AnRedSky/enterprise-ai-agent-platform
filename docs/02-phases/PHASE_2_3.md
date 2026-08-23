# Phase 2.3 — Model Provider Governance

> 状态：**2.3-A / 2.3-B / 2.3-C / 2.3-D 已实现；2.3-D 待完整 acceptance。**

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

## 2.3-C Runtime Governance Invocation Service + WorkflowRuntime 接入 — 已实现

已完成：

- `backend/app/services/runtime_model_governance.py`
- `backend/app/runtime/workflow_runtime.py`
- `backend/tests/unit/test_runtime_model_governance.py`
- `backend/tests/unit/test_workflow_runtime.py`
- `backend/tests/api_real/test_runtime_model_governance_api.py`

Runtime 主链路：

1. 读取已发布 `AgentVersion.model_profile_id`；
2. 有 `model_profile_id` 时使用 `explicit_profile`；
3. 无 `model_profile_id` 时使用 `organization_default`；
4. organization scope 从 Workflow execution tenant 对应的 active Organization 获取；
5. 通过 `RuntimeModelGovernanceService` 解析真实 PostgreSQL Provider/Profile；
6. 调用 `ModelGateway` 时显式传入 governed profile/provider；
7. fallback 仅接受 2.3-A 定义的 connectivity / timeout / rate limit / provider 5xx；
8. 不允许静默 Mock fallback。

## 2.3-D Runtime Usage / Trace Identity — 已实现基础能力

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

Real API bootstrap 问题已定位：bootstrap 原先在创建可执行 Workflow/Execution retry/circuit fixtures 后才创建 Organization；Runtime execution 已要求 active Organization membership，因此 fixture run 从预期的 `404` 变为 `403 当前用户没有有效的 Organization membership`。

修复方案已直接提交 `main`：bootstrap 先建立 Organization tenant，再创建所有需要运行的 Workflow fixtures；同时使用本次 bootstrap 专用 executable workflow，避免复用可能来自旧 tenant 状态的历史 workflow。

本轮 Real API 尚未重新执行，因此不得标记为 Passed。Migration/head verification 本轮也未收到执行结果，保持 Pending。

## 下一执行任务

**2.3-E Governed fallback success path + deterministic multi-provider acceptance**：完成 Real API Gate 重跑并确认 bootstrap tenant 修复后，补充真实可控 Provider adapter/fixture（不得以 Mock Provider 伪造 governed success），验证 candidate 顺序、bounded fallback、成功 outcome usage identity 与 fallback attempt trace；随后形成 Phase 2.3 acceptance gate。

若后续引入持久化 routing policy / pricing / usage record，必须先新增 Alembic Migration，再实现依赖该结构的业务代码。

## Gate 纪律

```powershell
cd backend
uv run pytest -q tests/unit/test_model_provider_governance_contract.py tests/api_contract/test_api_model_provider_governance.py tests/unit/test_runtime_model_governance.py tests/unit/test_workflow_runtime.py
uv run pytest -q
uv run alembic upgrade head
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests.ps1
```

上述命令必须由开发者本地实际执行；未执行的结果不得标记为 Passed。
