# Phase 2.3 Acceptance

## 当前验收状态

- Phase：2.3 Model Provider Governance
- 2.3-A Contract：已实现
- 2.3-B Backend Domain + API Contract：已实现
- 2.3-C Runtime Governance Invocation：已实现
- 2.3-D Runtime Usage / Trace Identity：已实现基础能力
- **2.3-E Governed fallback success：Passed**
- 2.3-F Fallback Policy Enforcement：待本地验证

## 2.3-E 实际验收证据

开发者在 `main` 的 `d0b7a2e` 实际执行：

```text
Targeted runtime governance tests: 30 passed
Backend default regression: 348 passed, 34 deselected
Alembic upgrade head: passed
Tenant Safe Real API Gate: 34 passed
```

2.3-E Real API Gate 已覆盖 governed provider/profile、真实 HTTP OpenAI-compatible fixture、provider 5xx fallback、deterministic candidate ordering、attempt request identity、trace identity、usage identity 与 Secret boundary。

此前 timeout fallback reason 不一致已修复，并补充了 HTTPX write/pool timeout 分类测试。

## 2.3-F 当前状态

提交 `dd037f8`：`fix(runtime): enforce governed fallback policy`

目标是使 `FallbackPolicy.enabled`、`eligible_reasons` 与最大 2 次 attempts 成为 Runtime 的真实执行约束。

**注意：`dd037f8` 之后的新增测试尚未由开发者本地执行，因此不得记录为 Passed。**

## 下一 Gate

```powershell
cd backend
uv run pytest -q tests/unit/test_model_provider_governance_contract.py tests/api_contract/test_api_model_provider_governance.py tests/unit/test_runtime_model_governance.py tests/unit/test_workflow_runtime.py
uv run pytest -q
uv run alembic upgrade head
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test\api-real\01_run_real_api_tests_tenant_safe.ps1
```

2.3-F 全部 Gate 通过后，进入 2.3-G Cost / Usage Accounting；若需要持久化，Migration 必须先于业务实现。
