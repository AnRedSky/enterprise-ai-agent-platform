import { expect, test, type APIRequestContext } from "@playwright/test";

function normalizeApiOrigin(value: string): string { return value.replace(/\/+$/, "").replace(/\/api\/v1$/, ""); }
const apiOrigin = normalizeApiOrigin(process.env.API_BASE_URL || "http://127.0.0.1:8000/api/v1");
const apiPath = (path: string): string => `/api/v1${path.startsWith("/") ? path : `/${path}`}`;
const accessTokenStorageKey = "enterprise_agent_access_token";
const rolesStorageKey = "enterprise_agent_roles";
const userIdStorageKey = "enterprise_agent_user_id";

async function waitForPersistedTrigger(api: APIRequestContext, workflowId: string, triggerName: string, headers: Record<string, string>) {
  const timeoutMs = 15_000; const intervalsMs = [500, 1000, 2000]; const deadline = Date.now() + timeoutMs; let attempt = 0; let lastItems: unknown[] = [];
  while (Date.now() < deadline) {
    const response = await api.get(apiPath(`/workflows/${workflowId}/triggers`), { headers }); expect(response.ok()).toBeTruthy(); const body = await response.json(); const items = Array.isArray(body) ? body : body.items; lastItems = Array.isArray(items) ? items : [];
    const trigger = lastItems.find((item): item is { name: string; id: string } => typeof item === "object" && item !== null && "name" in item && item.name === triggerName); if (trigger) return trigger;
    const interval = intervalsMs[Math.min(attempt, intervalsMs.length - 1)]; attempt += 1; await new Promise((resolve) => setTimeout(resolve, interval));
  }
  throw new Error(`等待 Workflow Trigger 持久化超时: workflow=${workflowId}, trigger=${triggerName}, items=${JSON.stringify(lastItems)}`);
}
async function waitForTriggerStatus(api: APIRequestContext, workflowId: string, triggerId: string, headers: Record<string, string>, status: string) {
  await expect.poll(async () => { const response = await api.get(apiPath(`/workflows/${workflowId}/triggers`), { headers }); expect(response.ok()).toBeTruthy(); const body = await response.json(); const items = Array.isArray(body) ? body : body.items; return items?.find((item: { id: string }) => item.id === triggerId)?.status; }, { timeout: 15_000, intervals: [500, 1000, 2000] }).toBe(status);
}
async function confirmMessageBox(page: import("@playwright/test").Page) { const dialog = page.locator(".el-message-box:visible"); await expect(dialog).toBeVisible(); await dialog.locator(".el-message-box__btns .el-button--primary").click(); }

test("Workflow Trigger Governance completes the real scheduled browser contract", async ({ page, playwright }) => {
  test.setTimeout(60_000); const unique = Date.now(); const username = `e2e-workflow-trigger-${unique}`; const password = "TestPassword123!"; const api: APIRequestContext = await playwright.request.newContext({ baseURL: apiOrigin });
  try {
    const register = await api.post(apiPath("/auth/register"), { data: { username, password } }); expect(register.ok()).toBeTruthy(); const login = await api.post(apiPath("/auth/login"), { data: { username, password } }); expect(login.ok()).toBeTruthy(); const loginBody = await login.json(); const token = loginBody.access_token as string; expect(token).toBeTruthy(); const headers = { Authorization: `Bearer ${token}` };
    const workflowResponse = await api.post(apiPath("/workflows"), { headers, data: { name: `E2E Scheduled Workflow ${unique}`, description: "Browser E2E scheduler persistence contract" } }); expect(workflowResponse.status()).toBe(201); const workflow = await workflowResponse.json();
    const versionResponse = await api.post(apiPath(`/workflows/${workflow.id}/versions`), { headers, data: { definition: { nodes: [{ id: "input", type: "input", config: {} }, { id: "output", type: "output", config: {} }], edges: [{ source: "input", target: "output" }] } } }); expect(versionResponse.status()).toBe(201); const version = await versionResponse.json();
    const publishResponse = await api.post(apiPath(`/workflows/${workflow.id}/versions/${version.id}/publish`), { headers }); expect(publishResponse.status()).toBe(200);
    const workflowDetailResponse = await api.get(apiPath(`/workflows/${workflow.id}`), { headers }); expect(workflowDetailResponse.ok()).toBeTruthy(); const publishedWorkflow = await workflowDetailResponse.json(); expect(publishedWorkflow).toMatchObject({ id: workflow.id, status: "published" });
    await page.addInitScript(({ token: accessToken, roles, userId, tokenKey, rolesKey, userIdKey }) => { localStorage.setItem(tokenKey, accessToken); localStorage.setItem(rolesKey, JSON.stringify(roles || [])); localStorage.setItem(userIdKey, userId); }, { token, roles: loginBody.roles || [], userId: loginBody.user_id, tokenKey: accessTokenStorageKey, rolesKey: rolesStorageKey, userIdKey: userIdStorageKey });
    await page.goto("/workflows/triggers"); await expect(page.getByText("Workflow Trigger Governance", { exact: true })).toBeVisible();
    await page.getByText("选择 Workflow", { exact: true }).click(); await page.getByRole("option", { name: new RegExp(`^${publishedWorkflow.name} \\(${publishedWorkflow.status}\\)$`) }).click();
    const triggerName = `Scheduled Trigger ${unique}`; await page.getByLabel("Trigger 名称").fill(triggerName); await page.getByTestId("workflow-trigger-type-select").click(); await page.getByRole("option", { name: "scheduled" }).click(); await page.getByRole("button", { name: "创建 Trigger" }).click();
    const triggerRow = page.getByRole("row").filter({ hasText: triggerName }); await expect(triggerRow).toBeVisible(); const persistedCreatedTrigger = await waitForPersistedTrigger(api, workflow.id, triggerName, headers); expect(persistedCreatedTrigger).toMatchObject({ trigger_type: "scheduled", status: "enabled", config: { timezone: "UTC", interval_seconds: 60, misfire_policy: "skip", catch_up_limit: 10 } });
    await expect.poll(async () => { const response = await api.get(apiPath(`/workflows/${workflow.id}/triggers/${persistedCreatedTrigger.id}/schedule`), { headers }); if (response.status() === 404) return undefined; expect(response.ok()).toBeTruthy(); return response.json(); }, { timeout: 15_000, intervals: [500, 1000, 2000] }).toMatchObject({ trigger_id: persistedCreatedTrigger.id, workflow_id: workflow.id, tenant_id: workflow.tenant_id, status: "enabled", timezone: "UTC", misfire_policy: "skip", catch_up_limit: 10, lease_active: expect.any(Boolean) });
    await triggerRow.getByRole("button", { name: "调度状态" }).click(); const schedulerCard = page.locator(".scheduler-card"); await expect(schedulerCard).toBeVisible(); const schedulerRefresh = schedulerCard.getByRole("button", { name: "刷新" }); if (await schedulerCard.getByTestId("scheduler-timezone").count() === 0) await schedulerRefresh.click(); await expect(schedulerCard.getByTestId("scheduler-timezone")).toHaveText("UTC", { timeout: 15_000 }); await expect(schedulerCard.getByTestId("scheduler-misfire-policy")).toHaveText("skip"); await expect(schedulerCard.getByTestId("scheduler-catch-up-limit")).toHaveText("10");
    await triggerRow.getByRole("button", { name: "禁用" }).click(); await confirmMessageBox(page); await expect(triggerRow).toContainText("disabled"); await waitForTriggerStatus(api, workflow.id, persistedCreatedTrigger.id, headers, "disabled"); await triggerRow.getByRole("button", { name: "删除" }).click(); await confirmMessageBox(page); await expect(page.getByText("Trigger 已删除")).toBeVisible(); await expect(page.getByRole("row").filter({ hasText: triggerName })).toHaveCount(0);
  } finally { await api.dispose(); }
});
