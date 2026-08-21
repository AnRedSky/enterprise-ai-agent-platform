import { test, expect, type APIRequestContext } from "@playwright/test";

function normalizeApiOrigin(value: string): string {
  return value.replace(/\/+$/, "").replace(/\/api\/v1$/, "");
}

const apiOrigin = normalizeApiOrigin(process.env.API_BASE_URL || "http://127.0.0.1:8000/api/v1");
const apiPath = (path: string): string => `/api/v1${path.startsWith("/") ? path : `/${path}`}`;

test("Webhook browser runtime converges duplicate events and enforces lifecycle security", async ({ page, playwright }) => {
  test.setTimeout(60_000);

  const nonce = crypto.randomUUID().replaceAll("-", "").slice(0, 12);
  const username = `frontend_webhook_runtime_${nonce}`;
  const password = `FrontendE2E!${nonce}`;
  const triggerName = `Browser Webhook Runtime ${nonce}`;
  const secret = `WebhookSecret!${nonce}1234`;
  const eventId = `event-${nonce}`;
  const api: APIRequestContext = await playwright.request.newContext({ baseURL: apiOrigin });

  try {
    const register = await api.post(apiPath("/auth/register"), { data: { username, password } });
    expect([200, 201]).toContain(register.status());
    const login = await api.post(apiPath("/auth/login"), { data: { username, password } });
    expect(login.ok()).toBeTruthy();
    const token = (await login.json()).access_token as string;
    const headers = { Authorization: `Bearer ${token}` };

    const workflowResponse = await api.post(apiPath("/workflows"), {
      headers,
      data: { name: `Browser Webhook Runtime ${nonce}`, description: "Phase 1.8-E browser runtime fixture" },
    });
    expect(workflowResponse.status()).toBe(201);
    const workflow = await workflowResponse.json();

    const versionResponse = await api.post(apiPath(`/workflows/${workflow.id}/versions`), {
      headers,
      data: {
        definition: {
          nodes: [
            { id: "input", type: "input", config: {} },
            { id: "output", type: "output", config: {} },
          ],
          edges: [],
        },
      },
    });
    expect(versionResponse.status()).toBe(201);
    const version = await versionResponse.json();
    const publishResponse = await api.post(apiPath(`/workflows/${workflow.id}/versions/${version.id}/publish`), { headers });
    expect(publishResponse.status()).toBe(200);

    await page.goto("/login");
    await page.getByLabel("用户名").fill(username);
    await page.getByLabel("密码").fill(password);
    await page.getByRole("button", { name: "登录" }).click();
    await expect(page).toHaveURL(/\/dashboard$/);

    await page.goto("/workflows/triggers");
    await expect(page.getByText("Workflow Trigger Governance")).toBeVisible();

    const workflowFormItem = page.locator(".el-form-item").filter({ hasText: "Workflow" }).first();
    await workflowFormItem.locator(".el-select").click();
    const workflowOption = page
      .locator(".el-select-dropdown:visible .el-select-dropdown__item")
      .filter({ hasText: `${workflow.name} (published)` })
      .first();
    await expect(workflowOption).toBeVisible();
    await workflowOption.click();

    await page.getByLabel("Trigger 名称").fill(triggerName);
    const triggerTypeFormItem = page.locator(".el-form-item").filter({ hasText: "类型" }).first();
    await triggerTypeFormItem.locator(".el-select").click();
    const webhookOption = page
      .locator(".el-select-dropdown:visible .el-select-dropdown__item")
      .filter({ hasText: "webhook" })
      .first();
    await expect(webhookOption).toBeVisible();
    // Element Plus re-renders the dropdown item while the selection popup settles.
    // Use the option's keyboard activation instead of a pointer click so Playwright
    // does not wait for a transient DOM node to become geometrically stable.
    await webhookOption.press("Enter");

    await page.getByLabel("Webhook Secret").fill(secret);
    await page.getByRole("button", { name: "创建 Trigger" }).click();

    const triggerRow = page.locator(".el-table__body-wrapper tbody tr").filter({ hasText: triggerName });
    await expect(triggerRow).toBeVisible();
    await expect(triggerRow).toContainText("webhook");
    await expect(triggerRow).toContainText("已配置");

    const persisted = await api.get(apiPath(`/workflows/${workflow.id}/triggers`), { headers });
    expect(persisted.ok()).toBeTruthy();
    const persistedItems = await persisted.json();
    const persistedTrigger = persistedItems.find((item: { name: string }) => item.name === triggerName);
    expect(persistedTrigger).toMatchObject({ trigger_type: "webhook", status: "enabled" });
    expect(persistedTrigger.config.secret_hash).toBeUndefined();

    const webhookPath = apiPath(`/webhooks/${persistedTrigger.id}`);
    const payload = { event_id: eventId, source: "browser-e2e", value: nonce };
    const first = await api.post(webhookPath, {
      headers: { "X-Webhook-Secret": secret, "Idempotency-Key": eventId },
      data: payload,
    });
    expect(first.status()).toBe(202);
    const firstBody = await first.json();
    expect(firstBody).toMatchObject({ status: "accepted", idempotency_key: `webhook:${persistedTrigger.id}:${eventId}` });
    expect(firstBody.execution_id).toBeTruthy();

    const duplicate = await api.post(webhookPath, {
      headers: { "X-Webhook-Secret": secret, "Idempotency-Key": eventId },
      data: payload,
    });
    expect(duplicate.status()).toBe(200);
    const duplicateBody = await duplicate.json();
    expect(duplicateBody).toMatchObject({
      status: "duplicate",
      execution_id: firstBody.execution_id,
      idempotency_key: firstBody.idempotency_key,
    });

    const invalidSecret = await api.post(webhookPath, {
      headers: { "X-Webhook-Secret": `${secret}-invalid`, "Idempotency-Key": `invalid-${eventId}` },
      data: payload,
    });
    expect(invalidSecret.status()).toBe(401);

    await expect.poll(
      async () => {
        const executions = await api.get(apiPath(`/workflows/${workflow.id}/executions`), { headers });
        expect(executions.ok()).toBeTruthy();
        const items = await executions.json();
        const execution = items.find((item: { id: string }) => item.id === firstBody.execution_id);
        return execution ? { status: execution.status, id: execution.id } : null;
      },
      { timeout: 20_000, intervals: [500, 1000, 2000] },
    ).toMatchObject({ id: firstBody.execution_id, status: expect.any(String) });

    await triggerRow.getByRole("button", { name: "禁用" }).click();
    await expect(page.getByText("Trigger 已禁用")).toBeVisible();

    const disabled = await api.post(webhookPath, {
      headers: { "X-Webhook-Secret": secret, "Idempotency-Key": `disabled-${eventId}` },
      data: { ...payload, event_id: `disabled-${eventId}` },
    });
    expect(disabled.status()).toBe(409);

    await triggerRow.getByRole("button", { name: "删除" }).click();
    const deleteDialog = page.locator(".el-message-box:visible");
    await expect(deleteDialog).toBeVisible();
    await deleteDialog.locator(".el-message-box__btns .el-button--primary").click();
    await expect(page.getByText("Trigger 已删除")).toBeVisible();

    const deleted = await api.post(webhookPath, {
      headers: { "X-Webhook-Secret": secret, "Idempotency-Key": `deleted-${eventId}` },
      data: { ...payload, event_id: `deleted-${eventId}` },
    });
    expect(deleted.status()).toBe(404);
  } finally {
    await api.dispose();
  }
});
