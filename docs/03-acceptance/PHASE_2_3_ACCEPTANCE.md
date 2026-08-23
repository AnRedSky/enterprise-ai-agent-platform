# Phase 2.3 Acceptance

## 当前验收状态

- Phase：2.3 Model Provider Governance
- 2.3-A Contract：已实现
- 2.3-B Backend Domain + API Contract：已实现
- 2.3-C Runtime Governance Invocation：已实现
- 2.3-D Runtime Usage / Trace Identity：已实现基础能力
- **2.3-E Governed fallback success：Passed**
- **2.3-F Fallback Policy Enforcement：Passed**
- 2.3-G Cost / Usage Accounting：已实现第一版，待本地验证

## 2.3-E / 2.3-F 实际验收证据

开发者在最新 `main`（`843e19d`）实际执行：

```text
Targeted runtime governance tests: 33 passed
Backend default regression: 351 passed, 34 deselected
Alembic upgrade head: passed
Tenant Safe Real API Gate: 34 passed
```

2.3-E Real API Gate 已覆盖 governed provider/profile、真实 HTTP OpenAI-compatible fixture、provider 5xx fallback、deterministic candidate ordering、attempt request identity、trace identity、usage identity 与 Secret boundary。

2.3-F 已进一步验证 Runtime 强制执行 fallback `enabled`、`eligible_reasons` 与最大 attempts=2。

此前 timeout fallback reason 不一致已修复，并补充 HTTPX write/pool timeout 分类测试。

## 2.3-G 实现范围

已提交第一版 Cost / Usage Accounting：

1. 新增 `0023_model_usage_accounting` Alembic migration；
2. 新增 `model_usage_records` PostgreSQL 表；
3. 每个 governed provider attempt 在 `model.invocation` trace 同一事务中持久化 usage record；
4. 成功、失败、fallback attempt 都计入 request unit；
5. 有 token usage 时按 input/output token units 计量；
6. 支持 Model Profile `parameters.pricing` 的 pricing source/version/rates；
7. 支持 deterministic request/token cost calculation；
8. 新增 `GET /api/v1/usage/model` organization scoped 查询；
9. 新增 unit、API contract、Real API accounting tests；
10. 不把 endpoint、credential_ref 或 Secret 写入 usage record。

## 2.3-G 当前状态

**待本地验证。** 本轮新增代码尚未由开发者实际执行，当前不记录 Passed。

### Acceptance Gate

```powershell
cd backend
uv run pytest -q tests/unit/test_usage_accounting.py tests/api_contract/test_api_usage_accounting.py tests/unit/test_model_provider_governance_contract.py tests/api_contract/test_api_model_provider_governance.py tests/unit/test_runtime_model_governance.py tests/unit/test_workflow_runtime.py
uv run pytest -q
uv run alembic upgrade head
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

全部通过后，才能将 2.3-G 标记 Passed 并关闭 Phase 2.3；若测试失败，先修复真实问题并记录到 `docs/04-errors/`，再重新执行 Gate。
