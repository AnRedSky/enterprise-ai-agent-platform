import { test, expect, type APIRequestContext } from "@playwright/test";

function normalizeApiOrigin(value: string): string {
  return value.replace(/\/+$/, "").replace(/\/api\/v1$/, "");
}

const apiOrigin = normalizeApiOrigin(process.env.API_BASE_URL || "http://127.0.0.1:8000/api/v1");
const apiPath = (path: string): string => `/api/v1${path.startsWith("/") ? path : `/${path}`}`;

test("Workflow Trigger Governance completes the real scheduled browser contract", async ({ page, playwright }) => {
  const nonce = crypto.randomUUID().replaceAll("-", "").slice(0, 12);
  const username = `frontend_e2e_${nonce}`;
  const password = `FrontendE2E!${nonce}`;
  const api: APIRequestContext = await playwright.request.newContext({ baseURL: apiOrigin });

  try {
    const register = await api.post(apiPath("/auth/register"), { data: { username, password } });
    expect([200, 201]).toContain(register.status());

    const login = await api.post(apiPath("/auth/login"), { data: { username, password } });
    expect(login.ok()).toBeTruthy();
    const token = (await login.json()).access_token as string;
    expect(token).toBeTruthy();
    const headers = { Authorization: `Bearer ${token}` };

    const workflowResponse = await api.post(apiPath("/workflows"), {
      headers,
      data: { name: `Browser Scheduled Trigger E2E ${nonce}`, description: "Phase 1.7-D browser fixture" },
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
    await expect(page.getByText("Tenant 不由前端提交")).toBeVisible();

    const workflowFormItem = page.locator(".el-form-item").filter({ hasText: "Workflow" }).first();
    const workflowSelect = workflowFormItem.locator(".el-select");
    await expect(workflowSelect).toBeVisible();
    await workflowSelect.click();

    const workflowOption = page
      .locator(".el-select-dropdown:visible .el-select-dropdown__item")
      .filter({ hasText: `${workflow.name} (published)` })
      .first();
    await expect(workflowOption).toBeVisible();
    await workflowOption.click();

    await page.getByLabel("Trigger 名称").fill(`Browser Scheduled Trigger ${nonce}`);

    // Element Plus renders options in a teleported dropdown and animates them.
    // Use the select's keyboard contract instead of racing the transient option DOM.
    const triggerTypeFormItem = page.locator(".el-form-item").filter({ hasText: "类型" }).first();
    const triggerTypeSelect = triggerTypeFormItem.locator(".el-select");
    await triggerTypeSelect.click();
    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("Enter");

    const scheduleConfigFormItem = page.locator(".el-form-item").filter({ hasText: "Config JSON" }).first();
    const scheduleConfigTextarea = scheduleConfigFormItem.locator("textarea");
    await expect(scheduleConfigTextarea).toHaveValue(/\"timezone\"\s*:\s*\"UTC\"/);
    await expect(scheduleConfigTextarea).toHaveValue(/\"interval_seconds\"\s*:\s*60/);
    expect(JSON.parse(await scheduleConfigTextarea.inputValue())).toEqual({
      timezone: "UTC",
      interval_seconds: 60,
    });
    await page.getByRole("button", { name: "创建 Trigger" }).click();

    const triggerRow = page.locator(".el-table__body-wrapper tbody tr").filter({ hasText: `Browser Scheduled Trigger ${nonce}` });
    await expect(triggerRow).toContainText("scheduled");
    await expect(triggerRow).toContainText("UTC / 每 60 秒");
    await expect(triggerRow.getByRole("button", { name: "Invoke" })).toHaveCount(0);

    await triggerRow.getByRole("button", { name: "禁用" }).click();
    await expect(triggerRow).toContainText("disabled");

    await triggerRow.getByRole("button", { name: "启用" }).click();
    await expect(triggerRow).toContainText("enabled");

    const persisted = await api.get(apiPath(`/workflows/${workflow.id}/triggers`), { headers });
    expect(persisted.ok()).toBeTruthy();
    const persistedTriggers = await persisted.json();
    const persistedItems = Array.isArray(persistedTriggers) ? persistedTriggers : persistedTriggers.items;
    expect(persistedItems).toBeInstanceOf(Array);
    const persistedTrigger = persistedItems.find((item: { name: string }) => item.name === `Browser Scheduled Trigger ${nonce}`);
    expect(persistedTrigger).toMatchObject({ trigger_type: "scheduled", status: "enabled" });
    expect(persistedTrigger.config).toEqual({ timezone: "UTC", interval_seconds: 60 });

    await triggerRow.getByRole("button", { name: "删除" }).click();
    const deleteDialog = page.locator(".el-message-box:visible");
    await expect(deleteDialog).toBeVisible();
    await expect(deleteDialog).toContainText(`确认删除 Trigger「Browser Scheduled Trigger ${nonce}」？`);
    await deleteDialog.locator(".el-message-box__btns .el-button--primary").click();
    await expect(page.locator(".el-table__body-wrapper tbody tr").filter({ hasText: `Browser Scheduled Trigger ${nonce}` })).toHaveCount(0);
  } finally {
    await api.dispose();
  }
});
