import { test, expect, type APIRequestContext } from "@playwright/test";

function apiPath(path: string): string { return `/api/v1${path.startsWith("/") ? path : `/${path}`}`; }
function normalizeApiOrigin(value: string): string { return value.replace(/\/+$/, "").replace(/\/api\/v1$/, ""); }
async function loginInBrowser(page: import("@playwright/test").Page, username: string, password: string) { await page.goto("/login"); await page.getByLabel("用户名").fill(username); await page.getByLabel("密码").fill(password); await expect(page.getByRole("button", { name: "登录" })).toBeVisible(); await page.getByRole("button", { name: "登录" }).click(); await expect(page).toHaveURL(/\/dashboard$/); }
async function registerUser(api: APIRequestContext, username: string, password: string) { const response = await api.post(apiPath("/auth/register"), { data: { username, password } }); expect([200, 201]).toContain(response.status()); return response.json(); }
async function loginUser(api: APIRequestContext, username: string, password: string) { const response = await api.post(apiPath("/auth/login"), { data: { username, password } }); expect(response.ok()).toBeTruthy(); return response.json(); }
async function createOrganization(api: APIRequestContext, headers: Record<string, string>, name: string) { const response = await api.post(apiPath("/organizations"), { headers, data: { name } }); expect(response.status()).toBe(201); return response.json(); }
async function getMembership(api: APIRequestContext, organizationId: string, userId: string, headers: Record<string, string>) {
  const limit = 100;
  for (let offset = 0;; offset += limit) {
    const response = await api.get(apiPath(`/organizations/${organizationId}/members?offset=${offset}&limit=${limit}`), { headers });
    expect(response.ok()).toBeTruthy();
    const body = await response.json();
    const membership = body.items.find((item: { user_id: string }) => item.user_id === userId);
    if (membership) return membership;
    if (offset + body.items.length >= body.total) break;
  }
  throw new Error(`Organization membership not found for user ${userId}`);
}
async function confirmMessageBox(page: import("@playwright/test").Page) { const dialog = page.locator(".el-message-box:visible"); await expect(dialog).toBeVisible(); await dialog.locator(".el-message-box__btns .el-button--primary").click(); }
async function showMemberRow(page: import("@playwright/test").Page, userId: string) {
  const memberRow = page.locator(".el-table__body-wrapper tbody tr").filter({ hasText: userId });
  const nextPage = page.locator(".el-pagination button.btn-next");
  for (;;) {
    if (await memberRow.count() > 0) { await expect(memberRow).toBeVisible(); return memberRow; }
    if (await nextPage.count() === 0 || await nextPage.isDisabled()) break;
    await nextPage.click();
  }
  throw new Error(`Organization member row not found in rendered pages for user ${userId}`);
}

async function createOwnerFixture(api: APIRequestContext, prefix: string, nonce: string) {
  const username = `${prefix}_${nonce}`;
  const password = `OrganizationOwner!${nonce}`;
  const user = await registerUser(api, username, password);
  const login = await loginUser(api, username, password);
  return { username, password, user, body: login, headers: { Authorization: `Bearer ${login.access_token}` } };
}

test("Organization management completes the real owner browser contract", async ({ page, playwright }) => {
  test.setTimeout(60_000); const nonce = crypto.randomUUID().replaceAll("-", "").slice(0, 12); const api: APIRequestContext = await playwright.request.newContext({ baseURL: normalizeApiOrigin(process.env.API_BASE_URL || "http://127.0.0.1:8000/api/v1") });
  try {
    const owner = await createOwnerFixture(api, `organization_owner_e2e`, nonce); const memberUsername = `organization_member_e2e_${nonce}`; const memberPassword = `OrganizationMemberE2E!${nonce}`; const organization = await createOrganization(api, owner.headers, `Organization E2E ${nonce}`);
    const memberUser = await registerUser(api, memberUsername, memberPassword);
    const addMember = await api.post(apiPath(`/organizations/${organization.id}/members`), { headers: owner.headers, data: { user_id: memberUser.user_id, role: "member" } }); expect(addMember.status()).toBe(201); const member = await getMembership(api, organization.id, memberUser.user_id, owner.headers);
    await loginInBrowser(page, owner.username, owner.password); await page.goto("/organizations"); await expect(page.getByRole("heading", { name: "组织", exact: true })).toBeVisible();
    const organizationRow = page.getByRole("row").filter({ hasText: organization.name }); await expect(organizationRow).toBeVisible(); await organizationRow.getByRole("link", { name: "管理成员" }).click(); await expect(page.getByRole("heading", { name: organization.name, exact: true })).toBeVisible(); await expect(page.getByRole("heading", { name: "成员", exact: true })).toBeVisible();
    const memberRow = await showMemberRow(page, memberUser.user_id); await expect(memberRow).toContainText("成员（member）");
    await memberRow.getByRole("button", { name: "编辑" }).click(); await expect(page.getByRole("dialog", { name: "编辑成员" })).toBeVisible(); await page.getByRole("dialog").locator(".el-select").click(); await page.getByRole("option", { name: "管理员（admin）" }).click(); await page.getByRole("dialog", { name: "编辑成员" }).getByRole("button", { name: "保存" }).click(); await expect(page.getByText("成员角色已更新")).toBeVisible(); await expect(memberRow).toContainText("管理员（admin）");
    await memberRow.getByRole("button", { name: "暂停" }).click(); await expect(page.getByText("成员已暂停")).toBeVisible(); await expect(memberRow).toContainText("已暂停（suspended）"); await memberRow.getByRole("button", { name: "恢复" }).click(); await expect(page.getByText("成员已恢复")).toBeVisible(); await expect(memberRow).toContainText("已启用（active）");
    await page.getByRole("button", { name: "暂停组织" }).click(); await confirmMessageBox(page); await expect(page.getByText("组织已暂停")).toBeVisible(); await page.getByRole("button", { name: "恢复组织" }).click(); await confirmMessageBox(page); await expect(page.getByText("组织已恢复")).toBeVisible();
    await memberRow.getByRole("button", { name: "转移所有权" }).click(); await expect(page.locator(".el-message-box:visible")).toContainText(`确认将组织所有权转移给 ${memberUser.user_id}`); await confirmMessageBox(page); await expect(page.getByText("所有权转移成功")).toBeVisible(); await expect(memberRow).toContainText("所有者（owner）");
    const persisted = await getMembership(api, organization.id, memberUser.user_id, owner.headers); expect(persisted).toMatchObject({ status: "active", role: "owner" }); expect(member).toBeTruthy();
    const newOwner = await loginUser(api, memberUsername, memberPassword); const newOwnerHeaders = { Authorization: `Bearer ${newOwner.access_token}` }; const originalOwnerMembership = await getMembership(api, organization.id, owner.user.user_id, newOwnerHeaders); const restore = await api.post(apiPath(`/organizations/${organization.id}/members/${originalOwnerMembership.id}/transfer-owner`), { headers: newOwnerHeaders }); expect(restore.ok()).toBeTruthy();
  } finally { await api.dispose(); }
});

test("Organization browser governance enforces member and suspended-member boundaries", async ({ page, playwright }) => {
  test.setTimeout(60_000); const nonce = crypto.randomUUID().replaceAll("-", "").slice(0, 12); const api: APIRequestContext = await playwright.request.newContext({ baseURL: normalizeApiOrigin(process.env.API_BASE_URL || "http://127.0.0.1:8000/api/v1") });
  try {
    const owner = await createOwnerFixture(api, `organization_boundary_owner`, nonce); const memberUsername = `organization_boundary_member_${nonce}`; const memberPassword = `OrganizationBoundaryMember!${nonce}`; const organization = await createOrganization(api, owner.headers, `Organization Boundary E2E ${nonce}`);
    const memberUser = await registerUser(api, memberUsername, memberPassword); const addMember = await api.post(apiPath(`/organizations/${organization.id}/members`), { headers: owner.headers, data: { user_id: memberUser.user_id, role: "member" } }); expect(addMember.status()).toBe(201); const membership = await getMembership(api, organization.id, memberUser.user_id, owner.headers);
    await loginInBrowser(page, memberUsername, memberPassword); await page.goto(`/organizations/${organization.id}`); await expect(page.getByRole("heading", { name: organization.name })).toBeVisible(); await expect(page.getByRole("button", { name: "添加成员" })).toHaveCount(0); await expect(page.getByRole("button", { name: "暂停组织" })).toHaveCount(0); await expect(page.getByRole("button", { name: "转移所有权" })).toHaveCount(0); await expect(page.getByRole("button", { name: "编辑" })).toHaveCount(0);
    const suspend = await api.patch(apiPath(`/organizations/${organization.id}/members/${membership.id}`), { headers: owner.headers, data: { status: "suspended" } }); expect(suspend.ok()).toBeTruthy(); await page.reload(); await expect(page.getByRole("status")).toContainText("组织详情加载失败"); await expect(page.getByRole("status")).toContainText("当前用户无权访问该组织"); await expect(page.getByRole("heading", { name: organization.name })).toHaveCount(0);
  } finally { await api.dispose(); }
});

test("Organization owner transfer exposes owner-only browser controls", async ({ page, playwright }) => {
  test.setTimeout(60_000); const nonce = crypto.randomUUID().replaceAll("-", "").slice(0, 12); const api: APIRequestContext = await playwright.request.newContext({ baseURL: normalizeApiOrigin(process.env.API_BASE_URL || "http://127.0.0.1:8000/api/v1") });
  try {
    const owner = await createOwnerFixture(api, `organization_transfer_owner`, nonce); const newOwnerUsername = `organization_transfer_new_${nonce}`; const newOwnerPassword = `OrganizationTransferNew!${nonce}`; const organization = await createOrganization(api, owner.headers, `Organization Transfer E2E ${nonce}`);
    const newUser = await registerUser(api, newOwnerUsername, newOwnerPassword); const addMember = await api.post(apiPath(`/organizations/${organization.id}/members`), { headers: owner.headers, data: { user_id: newUser.user_id, role: "member" } }); expect(addMember.status()).toBe(201); const membership = await getMembership(api, organization.id, newUser.user_id, owner.headers); const transfer = await api.post(apiPath(`/organizations/${organization.id}/members/${membership.id}/transfer-owner`), { headers: owner.headers }); expect(transfer.ok()).toBeTruthy();
    await loginInBrowser(page, owner.username, owner.password); await page.goto(`/organizations/${organization.id}`); await expect(page.getByRole("button", { name: "添加成员" })).toBeVisible(); await expect(page.getByRole("button", { name: "转移所有权" })).toHaveCount(0); await page.evaluate(() => localStorage.clear()); await loginInBrowser(page, newOwnerUsername, newOwnerPassword); await page.goto(`/organizations/${organization.id}`); await expect(page.getByRole("button", { name: "添加成员" })).toBeVisible(); await expect(page.getByRole("button", { name: "转移所有权" })).toBeVisible();
    const newOwner = await loginUser(api, newOwnerUsername, newOwnerPassword); const newOwnerHeaders = { Authorization: `Bearer ${newOwner.access_token}` }; const originalOwnerMembership = await getMembership(api, organization.id, owner.user.user_id, newOwnerHeaders); const restore = await api.post(apiPath(`/organizations/${organization.id}/members/${originalOwnerMembership.id}/transfer-owner`), { headers: newOwnerHeaders }); expect(restore.ok()).toBeTruthy();
  } finally { await api.dispose(); }
});
