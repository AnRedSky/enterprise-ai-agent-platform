# 2026-08-27 Real API / Regression Gate Blockers

## 1. Backend Unit Collection Blocker

Local `uv run pytest -q` failed during collection because the unit contract imported `release_frontier_lease()` while the production repository module did not expose it.

Resolution: restored the repository primitive with owner validation, lease clearing, `flush()` only, and no commit of the caller-owned transaction.

Commit: `209f2157d1e93063aaad703934091370cbdb32ad`

Verification: not yet executed after the fix.

## 2. Real API Bootstrap — Existing Tenant Organization

The non-tenant-safe gate failed at organization creation with:

```text
POST /organizations -> 409
当前 Tenant 已存在 Organization
```

Resolution: the bootstrap now reuses the existing organization returned by `GET /organizations` when the API explicitly reports the tenant already has one, and fails closed if no organization can be returned.

## 3. Real API Bootstrap — Invalid DAG Fixture

The tenant-safe gate reached workflow publication but failed with:

```text
422: DAG Workflow 必须 包含非空 edges
```

The bootstrap fixtures were generating DAG definitions with empty `edges`. This was a test-fixture defect, not a reason to weaken the production DAG validator.

Resolution: all bootstrap DAG fixtures now contain valid explicit edges, including `input -> output` and `agent -> output` forms.

Commits: `1d62b15d1666d8965646f2fb915272a07a150355`, `1951415040f3e15880a57f1cca5dea025b70aed7`

## 4. Current testing state

These fixes are based on real local feedback supplied by the project operator. No corrected test suite is being declared PASS until it is rerun locally.

Required next execution order:

1. `uv run pytest -q`
2. `scripts/test/release/01_backend_regression_gate.ps1`
3. `scripts/test/api-real/01_run_real_api_tests_tenant_safe.ps1`
4. migration/head verification
5. frontend gate
6. E2E / manual Phase 2.7 scenarios

Only actual local output may be recorded as PASS.
