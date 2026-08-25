import { expect, test, type APIRequestContext } from "@playwright/test";

function normalizeApiOrigin(value: string): string {
  return value.replace(/\/+$/, "").replace(/\/api\/v1$/, "");
}

const apiOrigin = normalizeApiOrigin(process.env.API_BASE_URL || "http://127.0.0.1:8000/api/v1");
const apiPath = (path: string): string => `/api/v1${path.startsWith("/") ? path : `/${path}`}`;
const accessTokenStorageKey = "enterprise_agent_access_token";
const rolesStorageKey = "enterprise_agent_roles";
const userIdStorageKey = "enterprise_agent_user_id";

/**
 * 等待真实 API 持久化指定 Trigger，并返回后续调度状态查询所需的完整实体。
 *
 * 该等待逻辑用于覆盖浏览器创建 Trigger 后，Backend PostgreSQL 持久化与查询可见性之间的短暂时序窗口；
 * 不使用固定 sleep，也不构造测试假数据，只有真实 HTTP 返回目标实体后才继续。
 *
 * Args:
 *   api: Playwright API 请求上下文。
 *   workflowId: Workflow 标识。
 *   triggerName: 要等待的 Trigger 名称。
 *   headers: 真实登录返回的认证请求头。
 *
 * Returns:
 *   已从真实 Backend HTTP 查询到的 Trigger 实体。
 *
 * Raises:
 *   Error: 在限定时间内 Backend 仍未返回目标 Trigger 时抛出超时错误。
 */
async function waitForPersistedTrigger(
  api: APIRequestContext,
  workflowId: string,
  triggerName: string,
  headers: Record<string, string>,
) {
  const timeoutMs = 15_000;
  const intervalsMs = [500, 1000, 2000];
  const deadline = Date.now() + timeoutMs;
  let attempt = 0;
  let lastItems: unknown[] = [];

  while (Date.now() < deadline) {
    const response = await api.get(apiPath(`/workflows/${workflowId}/triggers`), { headers });
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    const items = Array.isArray(body) ? body : body.items;
    lastItems = Array.isArray(items) ? items : [];
    const trigger = lastItems.find(
      (item): item is { name: string; id: string } =>
        typeof item === "object" && item !== null && "name" in item && item.name === triggerName,
    );

    if (trigger) {
      return trigger;
    }

    const interval = intervalsMs[Math.min(attempt, intervalsMs.length - 1)];
    attempt += 1;
    await new Promise((resolve) => setTimeout(resolve, interval));
  }

  throw new Error(
    `等待 Workflow Trigger 持久化超时: workflow=${workflowId}, trigger=${triggerName}, items=${JSON.stringify(lastItems)}`,
  );
}

// Workflow Trigger Governance 完成真实的定时触发器浏览器契约验证。
test("Workflow Trigger Governance completes the real scheduled browser contract", async ({ page, playwright }) => {
  test.setTimeout(60_000);

  const unique = Date.now();
  const username = `e2e-workflow-trigger-${unique}`;
  const password = "TestPassword123!";
  const api: APIRequestContext = await playwright.request.newContext({ baseURL: apiOrigin });

  try {
    const register = await api.post(apiPath("/auth/register"), {
      data: { username, password },
    });
    expect(register.ok()).toBeTruthy();

    const login = await api.post(apiPath("/auth/login"), {
      data: { username, password },
    });
    expect(login.ok()).toBeTruthy();
    const loginBody = await login.json();
    const token = loginBody.access_token as string;
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
      data: { definition: { nodes: [], edges: [] } },
    });
    expect(versionResponse.ok()).toBeTruthy();
    const version = await versionResponse.json();

    const publishResponse = await api.post(apiPath(`/workflows/${workflow.id}/versions/${version.id}/publish`), { headers });
    expect(publishResponse.ok()).toBeTruthy();

    // 正式前端路由为 /workflows/triggers；不能使用不存在的旧路径 /workflow-triggers。
    // 路由守卫依赖前端 localStorage Session，因此浏览器上下文必须使用真实登录返回值建立正式 Session。
    await page.addInitScript(
      ({ token: accessToken, roles, userId, tokenKey, rolesKey, userIdKey }) => {
        localStorage.setItem(tokenKey, accessToken);
        localStorage.setItem(rolesKey, JSON.stringify(roles || []));
        localStorage.setItem(userIdKey, userId);
      },
      {
        token,
        roles: loginBody.roles || [],
        userId: loginBody.user_id,
        tokenKey: accessTokenStorageKey,
        rolesKey: rolesStorageKey,
        userIdKey: userIdStorageKey,
      },
    );

    await page.goto("/workflows/triggers");
    await expect(page.getByText("Workflow Trigger Governance", { exact: true })).toBeVisible();

    const triggerName = `Scheduled Trigger ${unique}`;
    await page.getByLabel("Trigger 名称").fill(triggerName);
    // Element Plus 的 el-select 内部 input 是 readonly，点击时可能被 suffix SVG 拦截；使用生产页面提供的稳定 test hook 点击 Select 根节点。
    await page.getByTestId("workflow-trigger-type-select").click();
    await page.getByRole("option", { name: "scheduled" }).click();
    await page.getByRole("button", { name: "创建 Trigger" }).click();

    const triggerRow = page.getByRole("row").filter({ hasText: triggerName });
    await expect(triggerRow).toBeVisible();
    await triggerRow.getByRole("button", { name: "调度状态" }).click();
    await expect(page.getByText("Scheduler 持久化状态", { exact: true })).toBeVisible();

    const persistedCreatedTrigger = await waitForPersistedTrigger(api, workflow.id, triggerName, headers);
    expect(persistedCreatedTrigger).toMatchObject({
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
