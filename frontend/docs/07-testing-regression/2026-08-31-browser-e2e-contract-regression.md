# Browser E2E Contract Regression — 2026-08-31

## Baseline

Local `npm run test:e2e` executed against the current frontend/backend integration environment reported 8 failures across organization, model-provider, scheduled-trigger and webhook flows.

## Root causes

### 1. Organization fixtures violated the current Tenant → Organization contract

The backend now guarantees one Organization for the active default Tenant and registration automatically creates an active OrganizationMembership for the newly registered user. Organization creation rejects a second Organization in the same Tenant with HTTP 409, and adding a user who is already a member returns a conflict. The E2E fixtures incorrectly created a second Organization and then added a user who was already a member, producing the observed 409/422 responses.

The tests were changed to discover the Organization returned by `GET /api/v1/organizations` and to discover existing Membership records instead of creating duplicate domain state.

### 2. Organization UI assertions used stale English labels

The production page currently renders Chinese labels such as `组织`, `创建组织`, `暂停组织`, `恢复组织`, `模型提供方 / 模型配置`, and `所有者（owner）`. The E2E tests still asserted obsolete labels such as `Organizations` and `创建 Organization`.

The tests now assert the current production UI contract.

### 3. Workflow publish fixtures used an empty Definition

The current Runtime Definition Contract rejects an empty `nodes` array for new Workflow versions. Scheduled and webhook E2E fixtures therefore failed at publish. The fixtures now use a minimal valid input → output workflow definition with a real edge.

### 4. Trigger lifecycle assertions depended on transient toast timing

`ElMessage.success()` is intentionally transient. Browser E2E previously waited for `Trigger 已禁用`, which can disappear while the real API persistence/load cycle is still completing. The tests now assert the durable Trigger `status=disabled` through the real API and the rendered row, while retaining the delete success notification where it is useful for the user-facing flow.

## Changes

- Align organization E2E fixtures with the one-Organization-per-Tenant backend contract.
- Align organization E2E selectors with the current Chinese production UI labels.
- Use a valid Runtime Definition in scheduled/webhook fixtures.
- Replace transient Trigger-disabled toast assertions with persisted-state assertions.
- Preserve real API calls, generated unique test identities, and browser authentication; no hard-coded business fixtures were introduced.

## Verification required locally

The GitHub-side change is code-complete, but browser E2E execution must still be performed in the user's local Windows environment because this workspace cannot execute against the local backend/browser stack.

```powershell
cd D:\works\AgentWorks\LocalDev\enterprise-ai-agent-platform

git fetch origin
git checkout frontend
git pull --ff-only origin frontend

cd frontend
npm test
npm run build
npm run test:e2e
npm run test:gate
npm run test:local:full
```

Do not record any of the above commands as passed until their real local output has been observed.

## Expected result

The previous 8 E2E failures should be removed by the fixture/contract corrections. Any remaining failure must be treated as a new runtime or UI contract defect and investigated from its actual HTTP response, browser trace, and current backend contract rather than weakening the assertion.
