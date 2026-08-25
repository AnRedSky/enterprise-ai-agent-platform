import { expect, test } from "@playwright/test";
import { createApiClient, apiPath, type ApiClient } from "./support/api-client";

// Workflow Trigger Governance completes the real scheduled browser contract.
test("Workflow Trigger Governance completes the real scheduled browser contract", async ({ page, request }) => {
  const api: ApiClient = createApiClient(request);
  const unique = Date.now();
  const email = `e2e-workflow-trigger-${unique}@example.com`;
  const password = "TestPassword123!";
  let token = "";

  try {
    const register = await api.post(apiPath("/auth/register"), {
      data: { email, password, name: `E2E Trigger User ${unique}` },
    });
    expect(register.ok()).toBeTruthy();

    const login = await api.post(apiPath("/auth/login"), {
      data: { email, password },
    });
    expect(login.ok()).toBeTruthy();
    const loginBody = await login.json();
    token = loginBody.access_token;
    expect(token).toBeTruthy();
    const headers = { Authorization: `Bearer ${token}` };

    const workflowResponse = await api.post(apiPath("/workflows"), {
      headers,
      data: {
        name: `E2E Scheduled Workflow ${unique}`,
        description: "Browser E2E scheduler persistence contract",
      },
    });
    expect(workflowResponse.ok()).toBeTruthy();
    const workflow = await workflowResponse.json();

    const versionResponse = await api.post(apiPath(`/workflows/${workflow.id}/versions`), {
      headers,
      data: {
        graph: { nodes: [], edges: [] },
      },
    });
    expect(versionResponse.ok()).toBeTruthy();
    const version = await versionResponse.json();

    const publishResponse = await api.post(apiPath(`/workflows/${workflow.id}/versions/${version.id}/publish`), { headers });
    expect(publishResponse.ok()).toBeTruthy();

    await page.goto("/workflow-triggers");
    await expect(page.getByText("Workflow Trigger Governance", { exact: true })).toBeVisible();

    const triggerName = `Scheduled Trigger ${unique}`;
    await page.getByLabel("Trigger 名称").fill(triggerName);
    await page.getByLabel("类型").click();
    await page.getByRole("option", { name: "scheduled" }).click();
    await page.getByRole("button", { name: "创建 Trigger" }).click();

    const triggerRow = page.getByRole("row").filter({ hasText: triggerName });
    await expect(triggerRow).toBeVisible();
    await triggerRow.getByRole("button", { name: "调度状态" }).click();
    await expect(page.getByText("Scheduler 持久化状态", { exact: true })).toBeVisible();

    const persistedCreatedTrigger = await expect.poll(
      async () => {
        const response = await api.get(apiPath(`/workflows/${workflow.id}/triggers`), { headers });
        expect(response.ok()).toBeTruthy();
        const body = await response.json();
        const items = Array.isArray(body) ? body : body.items;
        return items.find((item: { name: string }) => item.name === triggerName);
      },
      { timeout: 15_000, intervals: [500, 1000, 2000] },
    ).toMatchObject({
      trigger_type: "scheduled",
      status: "enabled",
      config: { timezone: "UTC", interval_seconds: 60 },
    });

    await expect.poll(
      async () => {
        const response = await api.get(apiPath(`/workflows/${workflow.id}/triggers/${persistedCreatedTrigger.id}/schedule`), { headers });
        if (response.status() === 404) return undefined;
        expect(response.ok()).toBeTruthy();
        return response.json();
      },
      { timeout: 15_000, intervals: [500, 1000, 2000] },
    ).toMatchObject({
      trigger_id: persistedCreatedTrigger.id,
      workflow_id: workflow.id,
      tenant_id: workflow.tenant_id,
      status: "enabled",
      timezone: "UTC",
      misfire_policy: "skip",
      catch_up_limit: 10,
      lease_active: expect.any(Boolean),
    });

    const schedulerCard = page.locator(".scheduler-card");
    await expect(schedulerCard).toBeVisible();
    await expect(schedulerCard.getByTestId("scheduler-timezone")).toHaveText("UTC");
    await expect(schedulerCard.getByTestId("scheduler-misfire-policy")).toHaveText("skip");
    await expect(schedulerCard.getByTestId("scheduler-catch-up-limit")).toHaveText("10");

    await triggerRow.getByRole("button", { name: "禁用" }).click();
    await expect(page.getByText("Trigger 已禁用")).toBeVisible();
    await expect(triggerRow).toContainText("disabled");

    await triggerRow.getByRole("button", { name: "启用" }).click();
    await expect(page.getByText("Trigger 已启用")).toBeVisible();
    await expect(triggerRow).toContainText("enabled");

    const persisted = await api.get(apiPath(`/workflows/${workflow.id}/triggers`), { headers });
    expect(persisted.ok()).toBeTruthy();
    const persistedTriggers = await persisted.json();
    const persistedItems = Array.isArray(persistedTriggers) ? persistedTriggers : persistedTriggers.items;
    expect(persistedItems).toBeInstanceOf(Array);
    const persistedTrigger = persistedItems.find((item: { name: string }) => item.name === triggerName);
    expect(persistedTrigger).toMatchObject({ trigger_type: "scheduled", status: "enabled" });
    expect(persistedTrigger.config).toEqual({ timezone: "UTC", interval_seconds: 60 });
  } finally {
    await api.dispose();
  }
});
