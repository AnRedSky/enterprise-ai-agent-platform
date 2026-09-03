import { test, expect, type APIRequestContext } from "@playwright/test";

function apiPath(path: string): string { return `/api/v1${path.startsWith("/") ? path : `/${path}`}`; }
function normalizeApiOrigin(value: string): string { return value.replace(/\/+$/, "").replace(/\/api\/v1$/, ""); }
const ownerUsername = process.env.BROWSER_E2E_OWNER_USERNAME || "browser_e2e_owner";
const ownerPassword = process.env.BROWSER_E2E_OWNER_PASSWORD || "BrowserE2EOwner!2026";
async function loginInBrowser(page: import("@playwright/test").Page, username: string, password: string) { await page.goto("/login"); await page.getByLabel("用户名").fill(username); await page.getByLabel("密码").fill(password); await page.getByRole("button", { name: "登录" }).click(); await expect(page).toHaveURL(/\/dashboard$/); }
async function loginOwner(api: APIRequestContext) { const response = await api.post(apiPath("/auth/login"), { data: { username: ownerUsername, password: ownerPassword } }); expect(response.ok()).toBeTruthy(); return response; }
async function getOrganization(api: APIRequestContext, headers: Record<string, string>) { const response = await api.get(apiPath("/organizations"), { headers }); expect(response.ok()).toBeTruthy(); const body = await response.json(); expect(body.items?.length).toBeGreaterThan(0); return body.items[0]; }
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

test("Organization management completes the real owner browser contract", async ({ page, playwright }) => {
  test.setTimeout(60_000); const nonce = crypto.randomUUID().replaceAll("-", "").slice(0, 12); const memberUsername = `organization_member_e2e_${nonce}`; const memberPassword = `OrganizationMemberE2E!${nonce}`; const api: APIRequestContext = await playwright.request.newContext({ baseURL: normalizeApiOrigin(process.env.API_BASE_URL || "http://127.0.0.1:8000/api/v1") });
  try {
    const memberRegister = await api.post(apiPath("/auth/register"), { data: { username: memberUsername, password: memberPassword } }); expect([200, 201]).toContain(memberRegister.status()); const memberUser = await memberRegister.json();
    const ownerLogin = await loginOwner(api); const ownerBody = await ownerLogin.json(); const headers = { Authorization: `Bearer ${ownerBody.access_token}` }; const organization = await getOrganization(api, headers); const member = await getMembership(api, organization.id, memberUser.user_id, headers);
    await loginInBrowser(page, ownerUsername, ownerPassword); await page.goto("/organizations"); await expect(page.getByRole("heading", { name: "组织" })).toBeVisible(); await expect(page.getByRole("link", { name: "管理成员" })).toBeVisible(); await page.getByRole("link", { name: "管理成员" }).first().click(); await expect(page.getByRole("heading", { name: organization.name })).toBeVisible(); await expect(page.getByRole("heading", { name: "成员", exact: true })).toBeVisible();
    const memberRow = page.locator(".el-table__body-wrapper tbody tr").filter({ hasText: memberUser.user_id }); await expect(memberRow).toBeVisible(); await expect(memberRow).toContainText("成员（member）");
    await memberRow.getByRole("button", { name: "编辑" }).click(); await expect(page.getByRole("dialog", { name: "编辑成员" })).toBeVisible(); await page.getByRole("dialog").locator(".el-select").click(); await page.getByRole("option", { name: "管理员（admin）" }).click(); await page.getByRole("dialog", { name: "编辑成员" }).getByRole("button", { name: "保存" }).click(); await expect(page.getByText("成员角色已更新")).toBeVisible(); await expect(memberRow).toContainText("管理员（admin）");
    await memberRow.getByRole("button", { name: "暂停" }).click(); await expect(page.getByText("成员已暂停")).toBeVisible(); await expect(memberRow).toContainText("已暂停（suspended）"); await memberRow.getByRole("button", { name: "恢复" }).click(); await expect(page.getByText("成员已恢复")).toBeVisible(); await expect(memberRow).toContainText("已启用（active）");
    await page.getByRole("button", { name: "暂停组织" }).click(); await confirmMessageBox(page); await expect(page.getByText("组织已暂停")).toBeVisible(); await page.getByRole("button", { name: "恢复组织" }).click(); await confirmMessageBox(page); await expect(page.getByText("组织已恢复")).toBeVisible();
    await memberRow.getByRole("button", { name: "转移所有权" }).click(); await expect(page.locator(".el-message-box:visible")).toContainText(`确认将组织所有权转移给 ${memberUser.user_id}`); await confirmMessageBox(page); await expect(page.getByText("所有权转移成功")).toBeVisible(); await expect(memberRow).toContainText("所有者（owner）");
    const persisted = await getMembership(api, organization.id, memberUser.user_id, headers); expect(persisted).toMatchObject({ status: "active", role: "owner" }); expect(member).toBeTruthy();
  } finally { await api.dispose(); }
});

test("Organization browser governance enforces member and suspended-member boundaries", async ({ page, playwright }) => {
  test.setTimeout(60_000); const nonce = crypto.randomUUID().replaceAll("-", "").slice(0, 12); const memberUsername = `organization_boundary_member_${nonce}`; const memberPassword = `OrganizationBoundaryMember!${nonce}`; const api: APIRequestContext = await playwright.request.newContext({ baseURL: normalizeApiOrigin(process.env.API_BASE_URL || "http://127.0.0.1:8000/api/v1") });
  try {
    const memberRegister = await api.post(apiPath("/auth/register"), { data: { username: memberUsername, password: memberPassword } }); expect([200, 201]).toContain(memberRegister.status()); const memberUser = await memberRegister.json(); const ownerLogin = await loginOwner(api); const ownerBody = await ownerLogin.json(); const ownerHeaders = { Authorization: `Bearer ${ownerBody.access_token}` }; const organization = await getOrganization(api, ownerHeaders); const membership = await getMembership(api, organization.id, memberUser.user_id, ownerHeaders);
    await loginInBrowser(page, memberUsername, memberPassword); await page.goto(`/organizations/${organization.id}`); await expect(page.getByRole("heading", { name: organization.name })).toBeVisible(); await expect(page.getByRole("button", { name: "添加成员" })).toHaveCount(0); await expect(page.getByRole("button", { name: "暂停组织" })).toHaveCount(0); await expect(page.getByRole("button", { name: "转移所有权" })).toHaveCount(0); await expect(page.getByRole("button", { name: "编辑" })).toHaveCount(0);
    const suspend = await api.patch(apiPath(`/organizations/${organization.id}/members/${membership.id}`), { headers: ownerHeaders, data: { status: "suspended" } }); expect(suspend.ok()).toBeTruthy(); await page.reload(); await expect(page.getByRole("alert")).toContainText("组织详情加载失败"); await expect(page.getByRole("heading", { name: organization.name })).toHaveCount(0);
  } finally { await api.dispose(); }
});

test("Organization owner transfer exposes owner-only browser controls", async ({ page, playwright }) => {
  test.setTimeout(60_000); const nonce = crypto.randomUUID().replaceAll("-", "").slice(0, 12); const newOwnerUsername = `organization_transfer_new_${nonce}`; const newOwnerPassword = `OrganizationTransferNew!${nonce}`; const api: APIRequestContext = await playwright.request.newContext({ baseURL: normalizeApiOrigin(process.env.API_BASE_URL || "http://127.0.0.1:8000/api/v1") });
  try {
    const newRegister = await api.post(apiPath("/auth/register"), { data: { username: newOwnerUsername, password: newOwnerPassword } }); expect([200, 201]).toContain(newRegister.status()); const newUser = await newRegister.json(); const oldLogin = await loginOwner(api); const oldBody = await oldLogin.json(); const oldHeaders = { Authorization: `Bearer ${oldBody.access_token}` }; const organization = await getOrganization(api, oldHeaders); const membership = await getMembership(api, organization.id, newUser.user_id, oldHeaders); const transfer = await api.post(apiPath(`/organizations/${organization.id}/members/${membership.id}/transfer-owner`), { headers: oldHeaders }); expect(transfer.ok()).toBeTruthy();
    await loginInBrowser(page, ownerUsername, ownerPassword); await page.goto(`/organizations/${organization.id}`); await expect(page.getByRole("button", { name: "添加成员" })).toBeVisible(); await expect(page.getByRole("button", { name: "转移所有权" })).toHaveCount(0); await page.evaluate(() => localStorage.clear()); await loginInBrowser(page, newOwnerUsername, newOwnerPassword); await page.goto(`/organizations/${organization.id}`); await expect(page.getByRole("button", { name: "添加成员" })).toBeVisible(); await expect(page.getByRole("button", { name: "转移所有权" })).toBeVisible();
  } finally { await api.dispose(); }
});
