import { test, expect, type APIRequestContext } from "@playwright/test";

function normalizeApiBaseUrl(value: string): string {
  const normalized = value.replace(/\/+$/, "");
  return normalized.endsWith("/api/v1") ? normalized : `${normalized}/api/v1`;
}

const apiBaseUrl = normalizeApiBaseUrl(process.env.API_BASE_URL || "http://127.0.0.1:8000/api/v1");

test("Workflow Trigger Governance completes the real browser contract", async ({ page, playwright }) => {
  const nonce = crypto.randomUUID().replaceAll("-", "").slice(0, 12);
  const username = `frontend_e2e_${nonce}`;
  const password = `FrontendE2E!${nonce}`;
  const api: APIRequestContext = await playwright.request.newContext({ baseURL: apiBaseUrl });

  try {
    const register = await api.post("/auth/register", { data: { username, password } });
    expect([200, 201]).toContain(register.status());

    const login = await api.post("/auth/login", { data: { username, password } });
    expect(login.ok()).toBeTruthy();
    const token = (await login.json()).access_token as string;
    expect(token).toBeTruthy();
    const headers = { Authorization: `Bearer ${token}` };

    const workflowResponse = await api.post("/workflows", {
      headers,
      data: { name: `Browser Trigger E2E ${nonce}`, description: "Phase 1.6-C browser fixture" },
    });
    expect(workflowResponse.status()).toBe(201);
    const workflow = await workflowResponse.json();

    const versionResponse = await api.post(`/workflows/${workflow.id}/versions`, {
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

    const publishResponse = await api.post(`/workflows/${workflow.id}/versions/${version.id}/publish`, { headers });
    expect(publishResponse.status()).toBe(200);

    await page.goto("/login");
    await page.getByLabel("用户名").fill(username);
    await page.getByLabel("密码").fill(password);
    await page.getByRole("button", { name: "登录" }).click();
    await expect(page).toHaveURL(/\/dashboard$/);

    await page.goto("/workflows/triggers");
    await expect(page.getByText("Workflow Trigger Governance")).toBeVisible();
    await expect(page.getByText("Tenant 不由前端提交")).toBeVisible();

    const workflowSelect = page.getByRole("combobox").first();
    await workflowSelect.click();
    await page.getByText(`${workflow.name} (published)`, { exact: true }).click();

    await page.getByLabel("Trigger 名称").fill(`Browser Manual Trigger ${nonce}`);
    await page.getByLabel("Config JSON").fill('{"source":"browser-e2e"}');
    await page.getByRole("button", { name: "创建 Trigger" }).click();

    const triggerRow = page.locator(".el-table__body-wrapper tbody tr").filter({ hasText: `Browser Manual Trigger ${nonce}` });
    await expect(triggerRow).toContainText("enabled");
    await expect(triggerRow.getByRole("button", { name: "Invoke" })).toBeEnabled();

    await page.getByLabel("Invoke Input JSON").fill('{"source":"browser-e2e"}');
    await triggerRow.getByRole("button", { name: "Invoke" }).click();
    await expect(page.getByText("最近一次 Trigger Execution")).toBeVisible();
    await expect(page.getByText("completed", { exact: true })).toBeVisible();

    await triggerRow.getByRole("button", { name: "禁用" }).click();
    await expect(triggerRow).toContainText("disabled");
    await expect(triggerRow.getByRole("button", { name: "Invoke" })).toBeDisabled();

    await triggerRow.getByRole("button", { name: "启用" }).click();
    await expect(triggerRow).toContainText("enabled");
    await expect(triggerRow.getByRole("button", { name: "Invoke" })).toBeEnabled();

    await triggerRow.getByRole("button", { name: "删除" }).click();
    await page.getByRole("button", { name: "确定" }).click();
    await expect(page.locator(".el-table__body-wrapper tbody tr").filter({ hasText: `Browser Manual Trigger ${nonce}` })).toHaveCount(0);
  } finally {
    await api.dispose();
  }
});
