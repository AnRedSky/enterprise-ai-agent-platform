import { test, expect, type APIRequestContext } from "@playwright/test";

function apiPath(path: string): string {
  return `/api/v1${path.startsWith("/") ? path : `/${path}`}`;
}

function normalizeApiOrigin(value: string): string {
  return value.replace(/\/+$/, "").replace(/\/api\/v1$/, "");
}

test("Organization management completes the real owner browser contract", async ({ page, playwright }) => {
  test.setTimeout(60_000);

  const nonce = crypto.randomUUID().replaceAll("-", "").slice(0, 12);
  const username = `organization_e2e_${nonce}`;
  const password = `OrganizationE2E!${nonce}`;
  const organizationName = `Browser Organization ${nonce}`;
  const memberUsername = `organization_member_e2e_${nonce}`;
  const memberPassword = `OrganizationMemberE2E!${nonce}`;
  const api: APIRequestContext = await playwright.request.newContext({
    baseURL: normalizeApiOrigin(process.env.API_BASE_URL || "http://127.0.0.1:8000/api/v1"),
  });

  try {
    const register = await api.post(apiPath("/auth/register"), {
      data: { username, password },
    });
    expect([200, 201]).toContain(register.status());

    const memberRegister = await api.post(apiPath("/auth/register"), {
      data: { username: memberUsername, password: memberPassword },
    });
    expect([200, 201]).toContain(memberRegister.status());
    const memberUser = await memberRegister.json();
    expect(memberUser.user_id).toBeTruthy();

    const login = await api.post(apiPath("/auth/login"), {
      data: { username, password },
    });
    expect(login.ok()).toBeTruthy();
    const token = (await login.json()).access_token as string;
    expect(token).toBeTruthy();
    const headers = { Authorization: `Bearer ${token}` };

    await page.goto("/login");
    await page.getByLabel("用户名").fill(username);
    await page.getByLabel("密码").fill(password);
    await page.getByRole("button", { name: "登录" }).click();
    await expect(page).toHaveURL(/\/dashboard$/);

    await page.goto("/organizations");
    await expect(page.getByRole("heading", { name: "Organizations" })).toBeVisible();
    await page.getByRole("button", { name: "创建 Organization" }).click();
    await expect(page.getByRole("dialog", { name: "创建 Organization" })).toBeVisible();
    await page.getByRole("dialog").getByLabel("名称").fill(organizationName);
    await page.getByRole("dialog").getByRole("button", { name: "创建" }).click();
    await expect(page.getByText("Organization 创建成功")).toBeVisible();

    const row = page.locator(".el-table__body-wrapper tbody tr").filter({ hasText: organizationName });
    await expect(row).toBeVisible();
    await row.getByRole("link", { name: "管理成员" }).click();
    await expect(page.getByRole("heading", { name: organizationName })).toBeVisible();
    await expect(page.getByRole("heading", { name: "成员", exact: true })).toBeVisible();

    const organizationResponse = await api.get(apiPath("/organizations"), { headers });
    expect(organizationResponse.ok()).toBeTruthy();
    const organizations = await organizationResponse.json();
    const organization = organizations.items.find((item: { name: string }) => item.name === organizationName);
    expect(organization).toBeTruthy();

    await page.getByRole("button", { name: "添加成员" }).click();
    await expect(page.getByRole("dialog", { name: "添加成员" })).toBeVisible();
    await page.getByRole("dialog").getByLabel("User ID").fill(memberUser.user_id);
    await page.getByRole("dialog").getByRole("button", { name: "添加" }).click();
    await expect(page.getByText("成员添加成功")).toBeVisible();

    const memberRow = page.locator(".el-table__body-wrapper tbody tr").filter({ hasText: memberUser.user_id });
    await expect(memberRow).toBeVisible();
    await expect(memberRow).toContainText("member");
    await memberRow.getByRole("button", { name: "编辑" }).click();
    await expect(page.getByRole("dialog", { name: "编辑成员" })).toBeVisible();
    await page.getByRole("dialog").locator(".el-select").click();
    await page.getByRole("option", { name: "Admin" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "保存" }).click();
    await expect(page.getByText("成员角色已更新")).toBeVisible();
    await expect(memberRow).toContainText("admin");

    await memberRow.getByRole("button", { name: "暂停" }).click();
    await expect(page.getByText("成员已暂停")).toBeVisible();
    await expect(memberRow).toContainText("suspended");
    await memberRow.getByRole("button", { name: "恢复" }).click();
    await expect(page.getByText("成员已恢复")).toBeVisible();
    await expect(memberRow).toContainText("active");

    await page.getByRole("button", { name: "暂停 Organization" }).click();
    const statusDialog = page.locator(".el-message-box:visible");
    await expect(statusDialog).toContainText("suspended");
    const statusConfirm = statusDialog.locator(".el-message-box__btns .el-button--primary");
    await expect(statusConfirm).toBeVisible();
    await statusConfirm.click();
    await expect(page.getByText("Organization 已暂停")).toBeVisible();
    await expect(page.getByText("Organization 当前已暂停。管理操作仍由后端授权策略控制。")).toBeVisible();

    await page.getByRole("button", { name: "恢复 Organization" }).click();
    const recoveryDialog = page.locator(".el-message-box:visible");
    await expect(recoveryDialog).toContainText("active");
    const recoveryConfirm = recoveryDialog.locator(".el-message-box__btns .el-button--primary");
    await expect(recoveryConfirm).toBeVisible();
    await recoveryConfirm.click();
    await expect(page.getByText("Organization 已恢复")).toBeVisible();

    await memberRow.getByRole("button", { name: "转移 Owner" }).click();
    const transferDialog = page.locator(".el-message-box:visible");
    await expect(transferDialog).toContainText(`确认将 Organization 所有权转移给 ${memberUser.user_id}`);
    const transferConfirm = transferDialog.locator(".el-message-box__btns .el-button--primary");
    await expect(transferConfirm).toBeVisible();
    await transferConfirm.click();
    await expect(page.getByText("所有权转移成功")).toBeVisible();
    await expect(memberRow).toContainText("owner");

    const persistedMembers = await api.get(apiPath(`/organizations/${organization.id}/members`), { headers });
    expect(persistedMembers.ok()).toBeTruthy();
    const membershipItems = (await persistedMembers.json()).items;
    expect(membershipItems.filter((item: { role: string }) => item.role === "owner")).toHaveLength(1);
    expect(membershipItems.find((item: { user_id: string }) => item.user_id === memberUser.user_id)).toMatchObject({
      status: "active",
      role: "owner",
    });
  } finally {
    await api.dispose();
  }
});
