# Phase 2.3 Real API Bootstrap：Governed Mock Agent 缺少 Provider/Profile

## 发生时间

2026-08-23

## 阶段

Phase 2.3 — Model Provider Governance / 2.3-E Real API Acceptance

## 现象

开发者执行：

```powershell
cd backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

Tenant Safe bootstrap 已成功进入 circuit breaker fixture，但执行：

```text
POST /workflows/executions/7eea630c-50ae-4da8-967b-6488f0c0ba54/run
-> expected HTTP 503, got 404
{"detail":"没有符合治理策略的 Model Provider/Profile"}
```

## 根因

Phase 2.3 Runtime 已经强制通过 PostgreSQL 中的 Model Provider/Profile 做治理解析。`RuntimeModelGovernanceService` 在没有候选 Provider/Profile 时会返回 HTTP 404，而 Real API bootstrap 的 retry/circuit fixture Agent 仍通过 legacy `model_id=mock-http-503` / `mock-slow-success` 创建，没有设置 `model_profile_id`。

因此 fixture 虽然具有确定性的 MockProvider 模型名称，但没有进入 governed Profile 路径；Runtime 按设计拒绝执行，而不是静默回退到 MockProvider。

## 修复

修改：

`backend/scripts/test/api-real/00_bootstrap_real_api_tenant_safe.py`

增加 tenant-safe bootstrap 专用的 governed mock fixture 创建流程：

1. 使用已建立并校验的 `ORGANIZATION_ID`；
2. 通过真实 HTTP `POST /model-providers` 创建 `provider_type=mock` Provider；
3. 通过真实 HTTP `POST /model-providers/{provider_id}/profiles` 创建 `chat` Model Profile；
4. 将 Profile 的 `model_name` 绑定为原 deterministic mock model id；
5. 创建 Agent 时显式写入 `model_profile_id`；
6. 发布 Agent Version；
7. monkey-patch bootstrap 的 `create_retry_agent`，确保 retry/circuit 所有 fixture 都使用 governed Profile。

这里的 `provider_type=mock` 仅用于 Real API bootstrap 的确定性边界场景；它不是生产 Runtime 的 fallback。Runtime 仍然从 PostgreSQL Provider/Profile 解析治理边界，并由 Model Gateway 根据明确的 mock provider 类型选择确定性 MockProvider。

## 验证要求

本修复提交时尚未由开发者本地重新执行 Real API Gate，因此不得声明 acceptance passed。

必须由开发者重新执行：

```powershell
cd backend
uv run pytest -q tests/unit/test_model_provider_governance_contract.py tests/api_contract/test_api_model_provider_governance.py tests/unit/test_runtime_model_governance.py tests/unit/test_workflow_runtime.py tests/api_real/test_runtime_model_governance_api.py
uv run pytest -q
uv run alembic upgrade head
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

重点确认：

- retry fixture 不再因缺少 governed Profile 返回 `404`；
- circuit breaker open fixture 能到达预期 `503/CIRCUIT_OPEN`；
- recovery fixture 能继续进入 HALF_OPEN recovery 场景；
- 2.3-E governed fallback success 使用真实 HTTP fixture server 的场景仍独立通过；
- trace/audit 不泄漏 endpoint、credential_ref 或 Secret。

## 关联规则

遵循 `docs/01-governance/DEVELOPMENT.md`：真实 API 必须本地实际执行；未执行结果不得记录为 Passed；工程错误进入 `docs/04-errors/`；所有变更直接提交 `main`。
