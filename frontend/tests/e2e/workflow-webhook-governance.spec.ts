import { test, expect, type APIRequestContext } from "@playwright/test";

function normalizeApiOrigin(value: string): string {
  return value.replace(/\/+$/, "").replace(/\/api\/v1$/, "");
}

const apiOrigin = normalizeApiOrigin(process.env.API_BASE_URL || "http://127.0.0.1:8000/api/v1");
const apiPath = (path: string): string => `/api/v1${path.startsWith("/") ? path : `/${path}`}`;

test("Workflow Trigger Governance completes the real webhook browser contract", async ({ page, playwright }) => {
  test.setTimeout(60_000);

  const nonce = crypto.randomUUID().replaceAll("-", "").slice(0, 12);
  const username = `frontend_webhook_e2e_${nonce}`;
  const password = `FrontendE2E!${nonce}`;
  const triggerName = `Browser Webhook Trigger ${nonce}`;
  const secret = `WebhookSecret!${nonce}1234`;
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
      data: { name: `Browser Webhook E2E ${nonce}`, description: "Phase 1.8-C browser fixture" },
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
      .filter({ hasText: `${workflow.name} (draft)` })
      .first();
    if (await workflowOption.count()) await workflowOption.click();
    else {
      const publishedOption = page
        .locator(".el-select-dropdown:visible .el-select-dropdown__item")
        .filter({ hasText: `${workflow.name} (published)` })
        .first();
      await expect(publishedOption).toBeVisible();
      await publishedOption.click();
    }

    await page.getByLabel("Trigger 名称").fill(triggerName);
    const triggerTypeFormItem = page.locator(".el-form-item").filter({ hasText: "类型" }).first();
    await triggerTypeFormItem.locator(".el-select").click();
    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("Enter");

    const secretInput = page.getByLabel("Webhook Secret");
    await expect(secretInput).toBeVisible();
    await secretInput.fill(secret);

    const configTextarea = page.locator(".el-form-item").filter({ hasText: "Config JSON" }).first().locator("textarea");
    await expect(configTextarea).toHaveValue(/event_id_field/);
    await page.getByRole("button", { name: "创建 Trigger" }).click();

    const triggerRow = page.locator(".el-table__body-wrapper tbody tr").filter({ hasText: triggerName });
    await expect(triggerRow).toBeVisible();
    await expect(triggerRow).toContainText("webhook");
    await expect(triggerRow).toContainText("event_id");
    await expect(triggerRow).toContainText("已配置");
    await expect(triggerRow.getByRole("button", { name: "Invoke" })).toHaveCount(0);

    const persisted = await api.get(apiPath(`/workflows/${workflow.id}/triggers`), { headers });
    expect(persisted.ok()).toBeTruthy();
    const persistedItems = await persisted.json();
    const persistedTrigger = persistedItems.find((item: { name: string }) => item.name === triggerName);
    expect(persistedTrigger).toMatchObject({ trigger_type: "webhook", status: "enabled" });
    expect(persistedTrigger.config).toMatchObject({ auth_mode: "secret", event_id_field: "event_id", secret_configured: true });
    expect(persistedTrigger.config.secret_hash).toBeUndefined();

    await triggerRow.getByRole("button", { name: "禁用" }).click();
    await expect(page.getByText("Trigger 已禁用")).toBeVisible();
    await expect(triggerRow).toContainText("disabled");

    await triggerRow.getByRole("button", { name: "删除" }).click();
    const deleteDialog = page.locator(".el-message-box:visible");
    await expect(deleteDialog).toBeVisible();
    await deleteDialog.locator(".el-message-box__btns .el-button--primary").click();
    await expect(page.getByText("Trigger 已删除")).toBeVisible();
    await expect(page.locator(".el-table__body-wrapper tbody tr").filter({ hasText: triggerName })).toHaveCount(0);
  } finally {
    await api.dispose();
  }
});
