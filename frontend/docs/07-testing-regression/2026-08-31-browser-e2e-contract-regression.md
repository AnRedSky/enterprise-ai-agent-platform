# Browser E2E Contract Regression — 2026-08-31

## Baseline

Local `npm run test:e2e` executed against the current frontend/backend integration environment previously reported failures across organization, model-provider, scheduled-trigger and webhook flows. The isolated runs narrowed the product-side regressions to fixture ownership, scheduler-card interaction, and confirmation-dialog handling, and those product/test-contract fixes were completed in the preceding remediation.

The latest local feedback is different: `npm run test:e2e` now reports 8 tests with 5 failures and 3 passes. All 5 failures stop at `loginOwner()` for Organization / Model Provider owner scenarios because the direct Playwright runner was invoked without the Browser E2E fixture reset.

## Root causes and remediation

### 1. Organization fixtures are deterministic and isolated

The current backend enforces one Organization per Tenant. Registration creates an active OrganizationMembership for a newly registered user, while Organization creation rejects a second Organization in the same Tenant. Browser owner scenarios therefore use the dedicated reset script to clear the Organization aggregate and recreate a deterministic local-only owner fixture.

The owner identity is configurable through `BROWSER_E2E_OWNER_USERNAME` / `BROWSER_E2E_OWNER_PASSWORD`, with safe local-test defaults. Organization and Model Provider owner scenarios authenticate through that fixture and discover the real Organization through `GET /api/v1/organizations`.

### 2. Direct `npm run test:e2e` does not establish the owner fixture

`frontend/package.json` defines `test:e2e` as the raw Playwright runner. It intentionally does not reset the database or create test accounts. When the local database does not already contain `browser_e2e_owner`, the owner login request fails before any Organization or Provider UI contract is exercised.

The correct isolated path is:

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
uv run python .\scripts\test\e2e\00_reset_browser_e2e_database.py

cd ..\frontend
npm run test:e2e -- tests/e2e/organization-management.spec.ts
npm run test:e2e -- tests/e2e/model-provider-governance.spec.ts
```

The preferred path is to use the dedicated isolated gates so the reset happens automatically before every scenario.

### 3. Full Frontend Regression previously bypassed the isolated E2E contract

`frontend/scripts/test/run-local-full-regression.ps1` previously called raw `npm run test:e2e` after checking service readiness. That allowed the full regression gate to run Browser scenarios against shared developer database state, despite the Browser E2E contract requiring deterministic owner fixtures and scenario isolation.

The regression script is now aligned with the existing isolated runner:

- Organization: `02_run_organization_e2e.ps1`;
- Model Provider: `03_run_model_provider_e2e.ps1`;
- Workflow Trigger: `01_run_workflow_trigger_e2e.ps1`;
- Webhook Governance: `00_run_isolated_test.ps1`;
- Webhook Runtime: `00_run_isolated_test.ps1`.

Each scenario gets a fresh Browser E2E database fixture and therefore cannot inherit owner-transfer or suspended-member state from another scenario.

### 4. Existing Browser contract fixes remain unchanged

The earlier remediation remains valid:

- Organization selectors use the current Chinese production UI contract;
- scheduled Trigger scheduler state is loaded only after the real `调度状态` interaction;
- Trigger disable operations confirm the visible message box before durable-state assertions;
- scheduled/webhook fixtures use a valid Runtime Definition with a real input → output edge;
- durable Trigger state is verified through real API persistence rather than transient toast timing.

## Changed files in this remediation

- `frontend/scripts/test/run-local-full-regression.ps1`
  - runs Browser E2E through isolated scenario gates;
  - never starts/stops local services;
  - does not require manual test data.
- `frontend/docs/07-testing-regression/2026-08-31-browser-e2e-contract-regression.md`
  - records the latest direct-run feedback and fixture root cause;
  - records the corrected Full Regression entrypoint.
- `docs/04-errors/2026-08-31-browser-e2e-direct-run-missing-fixture.md`
  - records the engineering error, impact, remediation and prevention rule.

## Local verification

### Recommended complete Frontend Regression

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend
npm run test:local:full
```

The script never starts or stops API, Scheduler, Worker, PostgreSQL or Redis. If required services are unavailable, E2E is reported as `NOT EXECUTED` with the normal local startup guidance.

### Recommended Organization / Model Provider gates

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend
.\scripts\test\e2e\02_run_organization_e2e.ps1
.\scripts\test\e2e\03_run_model_provider_e2e.ps1
```

### Direct Playwright runner

`npm run test:e2e -- <spec>` remains a low-level runner. If the local database does not already contain the deterministic owner fixture, execute the reset script first. Do not interpret a missing-fixture login failure as a product regression.

Do not record a test as passed until the actual local command output has been observed.

## Verification status

GitHub-side remediation is complete. No local browser/backend execution is claimed from this workspace. The next acceptance step is to run `npm run test:local:full` locally, followed by the required frontend targeted tests, full Vitest, production build and `test:gate` results already required by the frontend development guidelines. If an isolated Browser scenario still fails, investigate its real HTTP response, browser trace and current Backend Contract rather than weakening the assertion.
