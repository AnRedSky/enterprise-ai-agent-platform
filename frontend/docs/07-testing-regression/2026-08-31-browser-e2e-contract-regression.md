# Browser E2E Contract Regression — 2026-08-31

## Baseline

Local `npm run test:e2e` executed against the then-current frontend/backend integration environment reported failures across organization, model-provider, scheduled-trigger and webhook flows. The subsequent isolated runs narrowed the remaining failures to fixture ownership, scheduler-card interaction, and confirmation-dialog handling.

## Root causes and remediation

### 1. Organization fixtures violated the current Tenant → Organization contract

The current backend enforces one Organization per Tenant. Registration creates an active OrganizationMembership for a newly registered user, while Organization creation rejects a second Organization in the same Tenant. The previous E2E fixtures treated each registered user as a new owner and attempted to create duplicate organization state.

The Browser E2E reset script now clears the Organization aggregate and recreates a deterministic local-only owner fixture. The owner identity is configurable through `BROWSER_E2E_OWNER_USERNAME` / `BROWSER_E2E_OWNER_PASSWORD`, with safe local-test defaults. Organization and Model Provider owner scenarios authenticate through that fixture and discover the real Organization through `GET /api/v1/organizations`.

### 2. Organization UI assertions were stale

The production page renders Chinese labels such as `组织`, `管理成员`, `模型提供方 / 模型配置`, `暂停组织`, `恢复组织`, and `所有者（owner）`. The E2E tests are aligned with these current UI labels and use real membership state rather than synthetic owner assumptions.

### 3. Scheduled Trigger scheduler state is intentionally on-demand

The Trigger page follows the frontend governance rule that scheduler state is loaded on demand. The `.scheduler-card` is only rendered after the user selects `调度状态`. The scheduled E2E contract was incorrectly asserting the card before performing that user action.

The test now clicks `调度状态` after validating the persisted scheduler API contract, then verifies the rendered timezone, misfire policy and catch-up limit.

### 4. Trigger disable is a confirmed destructive/lifecycle action

The production Trigger page wraps enable/disable with `ElMessageBox.confirm()`. The E2E tests previously clicked `禁用` and immediately asserted persisted state without confirming the dialog. This made the backend state correctly remain `enabled`.

The scheduled and webhook E2E tests now explicitly confirm the visible message box before asserting the durable `disabled` state through both the rendered row and real API polling. Delete confirmation remains explicit as well.

### 5. Workflow fixtures must use a valid Runtime Definition

Scheduled and webhook fixtures use a minimal input → output workflow definition with a real edge, matching the current Runtime Definition Contract and avoiding empty-node publish failures.

## Changed files

- `backend/scripts/test/e2e/00_reset_browser_e2e_database.py`
  - resets Organization state;
  - creates a deterministic local E2E owner;
  - supports environment overrides for owner credentials.
- `frontend/tests/e2e/organization-management.spec.ts`
  - uses the seeded owner fixture and generated member users;
  - verifies owner/member/suspended-member boundaries against real API state.
- `frontend/tests/e2e/model-provider-governance.spec.ts`
  - uses the seeded owner fixture for owner-only Provider/Profile operations.
- `frontend/tests/e2e/workflow-trigger-governance.spec.ts`
  - performs the real `调度状态` interaction;
  - confirms Trigger disable before durable-state assertions.
- `frontend/tests/e2e/workflow-webhook-governance.spec.ts`
  - confirms Trigger disable before durable-state assertions.
- `frontend/tests/e2e/workflow-webhook-runtime.spec.ts`
  - confirms Trigger disable before validating webhook rejection after lifecycle transition.

## Local verification

Browser E2E must be executed against the local backend/browser stack. The isolated runner is the preferred path because it resets the database and creates the owner fixture before each scenario:

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\frontend

.\scripts\test\e2e\02_run_organization_e2e.ps1
.\scripts\test\e2e\02_run_model_provider_governance_e2e.ps1
.\scripts\test\e2e\01_run_workflow_trigger_e2e.ps1
npm run test:e2e -- tests/e2e/workflow-webhook-governance.spec.ts
npm run test:e2e -- tests/e2e/workflow-webhook-runtime.spec.ts
```

For a direct `npm run test:e2e -- <spec>` invocation, run the reset script first if the local database does not already contain the deterministic owner fixture:

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform\backend
uv run python .\scripts\test\e2e\00_reset_browser_e2e_database.py

cd ..\frontend
npm run test:e2e -- tests/e2e/organization-management.spec.ts
npm run test:e2e -- tests/e2e/model-provider-governance.spec.ts
```

Do not record a test as passed until the actual local command output has been observed.

## Verification status

GitHub-side code changes are complete for the reported failures. No local browser/backend execution is claimed from this workspace. The next acceptance step is to run the isolated E2E scenarios locally, followed by `npm test`, `npm run build`, `npm run test:gate`, and the full local regression gate.
