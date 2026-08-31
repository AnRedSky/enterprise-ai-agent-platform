import { test, expect, type APIRequestContext } from "@playwright/test";

function apiPath(path: string): string {
  return `/api/v1${path.startsWith("/") ? path : `/${path}`}`;
}

function normalizeApiOrigin(value: string): string {
  return value.replace(/\/+$/, "").replace(/\/api\/v1$/, "");
}

async function loginInBrowser(page: import("@playwright/test").Page, username: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("用户名").fill(username);
  await page.getByLabel("密码").fill(password);
  await page.getByRole("button", { name: "登录" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

async function getOwnedOrganization(api: APIRequestContext, headers: Record<string, string>) {
  const response = await api.get(apiPath("/organizations"), { headers });
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  expect(body.items?.length).toBeGreaterThan(0);
  return body.items[0];
}

test("Model Provider/Profile owner browser contract uses organization scoped real APIs", async ({ page, playwright }) => {
  test.setTimeout(60_000);
  const nonce = crypto.randomUUID().replaceAll("-", "").slice(0, 12);
  const username = `model_provider_e2e_${nonce}`;
  const password = `ModelProviderE2E!${nonce}`;
  const organizationName = `Model Provider Organization ${nonce}`;
  const providerName = `Provider ${nonce}`;
  const profileName = `Embedding Profile ${nonce}`;
  const api: APIRequestContext = await playwright.request.newContext({
    baseURL: normalizeApiOrigin(process.env.API_BASE_URL || "http://127.0.0.1:8000/api/v1"),
  });
  let providerId = "";
  let profileId = "";
  let token = "";

  try {
    const register = await api.post(apiPath("/auth/register"), { data: { username, password } });
    expect([200, 201]).toContain(register.status());
    const login = await api.post(apiPath("/auth/login"), { data: { username, password } });
    expect(login.ok()).toBeTruthy();
    const loginBody = await login.json();
    token = loginBody.access_token as string;
    const headers = { Authorization: `Bearer ${token}` };
    const organization = await getOwnedOrganization(api, headers);
    expect(organization.name).toBeTruthy();

    await loginInBrowser(page, username, password);
    await page.goto(`/organizations/${organization.id}`);
    await expect(page.getByRole("button", { name: "模型提供方 / 模型配置" })).toBeVisible();
    await page.getByRole("button", { name: "模型提供方 / 模型配置" }).click();
    await expect(page).toHaveURL(new RegExp(`/organizations/${organization.id}/model-providers$`));

    await page.getByRole("button", { name: "创建 Provider" }).click();
    const providerDialog = page.getByRole("dialog", { name: "创建 Provider" });
    await providerDialog.getByLabel("名称").fill(providerName);
    await providerDialog.getByLabel("Provider Name").fill("governed-e2e-provider");
    await providerDialog.getByLabel("Credential Ref").fill("secret://e2e/model-provider");
    await providerDialog.getByRole("button", { name: "保存" }).click();
    await expect(page.getByText("Provider 保存成功")).toBeVisible();
    await expect(page.getByText(providerName, { exact: true })).toBeVisible();

    const providerList = await api.get(apiPath(`/model-providers?organization_id=${organization.id}`), { headers });
    expect(providerList.ok()).toBeTruthy();
    const provider = (await providerList.json()).items.find((item: { name: string }) => item.name === providerName);
    expect(provider).toBeTruthy();
    providerId = provider.id;

    const providerCard = page.locator(".provider-card").filter({ hasText: providerName });
    await providerCard.getByRole("button", { name: "创建 Profile" }).click();
    const profileDialog = page.getByRole("dialog", { name: "创建 Profile" });
    await profileDialog.getByRole("textbox", { name: /^\* 名称$/ }).fill(profileName);
    await profileDialog.locator(".el-select__wrapper").click();
    await page.getByRole("option", { name: "Embedding" }).click();
    await profileDialog.getByLabel("模型名称").fill("governed-e2e-embedding");
    await profileDialog.getByLabel("Dimension").fill("768");
    await profileDialog.getByRole("button", { name: "保存" }).click();
    await expect(page.getByText("Profile 保存成功")).toBeVisible();

    const profiles = await api.get(apiPath(`/model-providers/${providerId}/profiles`), { headers });
    expect(profiles.ok()).toBeTruthy();
    const profile = (await profiles.json()).find((item: { name: string }) => item.name === profileName);
    expect(profile).toMatchObject({ model_type: "embedding", dimension: 768 });
    profileId = profile.id;
    await expect(providerCard).toContainText(profileName);
    await expect(providerCard).toContainText("768");
  } finally {
    if (profileId && providerId && token) {
      await api.delete(apiPath(`/model-providers/model-profiles/${profileId}`), { headers: { Authorization: `Bearer ${token}` } });
    }
    if (providerId && token) {
      await api.delete(apiPath(`/model-providers/${providerId}`), { headers: { Authorization: `Bearer ${token}` } });
    }
    await api.dispose();
  }
});

test("Model Provider/Profile management button is hidden from organization members", async ({ page, playwright }) => {
  test.setTimeout(60_000);
  const nonce = crypto.randomUUID().replaceAll("-", "").slice(0, 12);
  const ownerUsername = `model_provider_boundary_owner_${nonce}`;
  const ownerPassword = `ModelProviderBoundaryOwner!${nonce}`;
  const memberUsername = `model_provider_boundary_member_${nonce}`;
  const memberPassword = `ModelProviderBoundaryMember!${nonce}`;
  const api: APIRequestContext = await playwright.request.newContext({
    baseURL: normalizeApiOrigin(process.env.API_BASE_URL || "http://127.0.0.1:8000/api/v1"),
  });

  try {
    const ownerRegister = await api.post(apiPath("/auth/register"), { data: { username: ownerUsername, password: ownerPassword } });
    const memberRegister = await api.post(apiPath("/auth/register"), { data: { username: memberUsername, password: memberPassword } });
    expect([200, 201]).toContain(ownerRegister.status());
    expect([200, 201]).toContain(memberRegister.status());
    const memberUser = await memberRegister.json();
    const ownerLogin = await api.post(apiPath("/auth/login"), { data: { username: ownerUsername, password: ownerPassword } });
    expect(ownerLogin.ok()).toBeTruthy();
    const ownerToken = (await ownerLogin.json()).access_token as string;
    const headers = { Authorization: `Bearer ${ownerToken}` };
    const organization = await getOwnedOrganization(api, headers);

    await loginInBrowser(page, memberUsername, memberPassword);
    await page.goto(`/organizations/${organization.id}`);
    await expect(page.getByRole("heading", { name: organization.name })).toBeVisible();
    await expect(page.getByRole("button", { name: "模型提供方 / 模型配置" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "添加成员" })).toHaveCount(0);
    expect(memberUser.user_id).toBeTruthy();
  } finally {
    await api.dispose();
  }
});