import { test, expect, type APIRequestContext } from "@playwright/test";

function apiPath(path: string): string { return `/api/v1${path.startsWith("/") ? path : `/${path}`}`; }
function normalizeApiOrigin(value: string): string { return value.replace(/\/+$/, "").replace(/\/api\/v1$/, ""); }
const ownerUsername = process.env.BROWSER_E2E_OWNER_USERNAME || "browser_e2e_owner";
const ownerPassword = process.env.BROWSER_E2E_OWNER_PASSWORD || "BrowserE2EOwner!2026";

async function loginInBrowser(page: import("@playwright/test").Page, username: string, password: string) {
  await page.goto("/login");
  await page.getByLabel("用户名").fill(username);
  await page.getByLabel("密码").fill(password);
  await expect(page.getByRole("button", { name: "登录" })).toBeVisible();
  await page.getByRole("button", { name: "登录" }).click();
  await expect(page).toHaveURL(/\/dashboard$/);
}

async function loginOwner(api: APIRequestContext) {
  const response = await api.post(apiPath("/auth/login"), { data: { username: ownerUsername, password: ownerPassword } });
  expect(response.ok()).toBeTruthy();
  return response.json();
}

async function getOrganization(api: APIRequestContext, headers: Record<string, string>, tenantId: string) {
  const response = await api.get(apiPath("/organizations"), { headers });
  expect(response.ok()).toBeTruthy();
  const body = await response.json();
  const organization = body.items.find((item: { tenant_id: string }) => item.tenant_id === tenantId);
  expect(organization).toBeTruthy();
  return organization;
}

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

async function confirmMessageBox(page: import("@playwright/test").Page) {
  const dialog = page.locator(".el-message-box:visible");
  await expect(dialog).toBeVisible();
  await dialog.locator(".el-message-box__btns .el-button--primary").click();
}

function waitForMessage(page: import("@playwright/test").Page, message: string) {
  return page.evaluate((expected) => new Promise<void>((resolve, reject) => {
    const timeout = window.setTimeout(() => {
      observer.disconnect();
      reject(new Error(`Expected Element Plus message was not observed: ${expected}`));
    }, 5_000);
    const isVisible = (element: Element) => {
      const node = element as HTMLElement;
      const style = window.getComputedStyle(node);
      return style.display !== "none" && style.visibility !== "hidden" && node.getClientRects().length > 0;
    };
    const findMessage = () => Array.from(document.querySelectorAll(".el-message"))
      .some((element) => isVisible(element) && (element.textContent || "").includes(expected));
    if (findMessage()) {
      window.clearTimeout(timeout);
      resolve();
      return;
    }
    const observer = new MutationObserver(() => {
      if (!findMessage()) return;
      observer.disconnect();
      window.clearTimeout(timeout);
      resolve();
    });
    observer.observe(document.body, { subtree: true, childList: true, characterData: true });
  }), message);
}

async function showMemberRow(page: import("@playwright/test").Page, userId: string) {
  const nextPage = page.locator(".el-pagination button.btn-next");
  for (;;) {
    const memberRow = page.getByRole("row").filter({ hasText: userId });
    if (await memberRow.count() > 0) {
      await expect(memberRow).toBeVisible();
      return memberRow;
    }
    if (await nextPage.count() === 0 || await nextPage.isDisabled()) break;
    const currentPage = page.locator(".el-pagination .number.is-active");
    const currentPageText = await currentPage.textContent();
    await nextPage.click();
    if (currentPageText) await expect(currentPage).not.toHaveText(currentPageText);
  }
  throw new Error(`Organization member row not found in rendered pages for user ${userId}`);
}

test("Organization management completes the real owner browser contract", async ({ page, playwright }) => {
  test.setTimeout(60_000);
  const nonce = crypto.randomUUID().replaceAll("-", "").slice(0, 12);
  const memberUsername = `organization_member_e2e_${nonce}`;
  const memberPassword = `OrganizationMemberE2E!${nonce}`;
  const api: APIRequestContext = await playwright.request.newContext({ baseURL: normalizeApiOrigin(process.env.API_BASE_URL || "http://127.0.0.1:8000/api/v1") });
  let ownershipTransferred = false;
  let organizationId: string | null = null;
  try {
    const memberRegister = await api.post(apiPath("/auth/register"), { data: { username: memberUsername, password: memberPassword } });
    expect([200, 201]).toContain(memberRegister.status());
    const memberUser = await memberRegister.json();
    const ownerBody = await loginOwner(api);
    const headers = { Authorization: `Bearer ${ownerBody.access_token}` };
    const organization = await getOrganization(api, headers, ownerBody.tenant_id);
    organizationId = organization.id;
    const member = await getMembership(api, organization.id, memberUser.user_id, headers);

    await loginInBrowser(page, ownerUsername, ownerPassword);
    await page.goto("/organizations");
    await expect(page.getByRole("heading", { name: "组织", exact: true })).toBeVisible();
    const organizationRow = page.getByRole("row").filter({ hasText: organization.name });
    await expect(organizationRow).toBeVisible();
    await organizationRow.getByRole("link", { name: "管理成员" }).click();
    await expect(page.getByRole("heading", { name: organization.name, exact: true })).toBeVisible();
    await expect(page.getByRole("heading", { name: "成员", exact: true })).toBeVisible();

    const memberRow = await showMemberRow(page, memberUser.user_id);
    await expect(memberRow).toContainText("成员（member）");
    await memberRow.getByRole("button", { name: "编辑" }).click();
    await expect(page.getByRole("dialog", { name: "编辑成员" })).toBeVisible();
    await page.getByRole("dialog").locator(".el-select").click();
    await page.getByRole("option", { name: "管理员（admin）" }).click();
    await page.getByRole("dialog", { name: "编辑成员" }).getByRole("button", { name: "保存" }).click();
    await expect(page.getByText("成员角色已更新")).toBeVisible();
    await expect(memberRow).toContainText("管理员（admin）");

    const suspendMemberResponse = page.waitForResponse((response) => response.ok()
      && response.request().method() === "PATCH"
      && response.url().includes(`/organizations/${organization.id}/members/${member.id}`));
    await memberRow.getByRole("button", { name: "暂停" }).click();
    await confirmMessageBox(page);
    await suspendMemberResponse;
    await expect(memberRow).toContainText("已暂停（suspended）");

    const restoreMemberResponse = page.waitForResponse((response) => response.ok()
      && response.request().method() === "PATCH"
      && response.url().includes(`/organizations/${organization.id}/members/${member.id}`));
    await memberRow.getByRole("button", { name: "恢复" }).click();
    await confirmMessageBox(page);
    await restoreMemberResponse;
    await expect(memberRow).toContainText("已启用（active）");

    const suspendedOrganizationMessage = waitForMessage(page, "组织已暂停");
    await page.getByRole("button", { name: "暂停组织" }).click();
    await confirmMessageBox(page);
    await suspendedOrganizationMessage;

    const restoredOrganizationMessage = waitForMessage(page, "组织已恢复");
    await page.getByRole("button", { name: "恢复组织" }).click();
    await confirmMessageBox(page);
    await restoredOrganizationMessage;

    await memberRow.getByRole("button", { name: "转移所有权" }).click();
    await expect(page.locator(".el-message-box:visible")).toContainText(`确认将组织所有权转移给 ${memberUser.user_id}`);
    await confirmMessageBox(page);
    await expect(page.getByText("所有权转移成功")).toBeVisible();
    ownershipTransferred = true;
    await expect(memberRow).toContainText("所有者（owner）");
    const persisted = await getMembership(api, organization.id, memberUser.user_id, headers);
    expect(persisted).toMatchObject({ status: "active", role: "owner" });
    expect(member).toBeTruthy();

    const newOwner = await api.post(apiPath("/auth/login"), { data: { username: memberUsername, password: memberPassword } });
    expect(newOwner.ok()).toBeTruthy();
    const newOwnerBody = await newOwner.json();
    const newOwnerHeaders = { Authorization: `Bearer ${newOwnerBody.access_token}` };
    const originalOwnerMembership = await getMembership(api, organization.id, ownerBody.user_id, newOwnerHeaders);
    const restore = await api.post(apiPath(`/organizations/${organization.id}/members/${originalOwnerMembership.id}/transfer-owner`), { headers: newOwnerHeaders });
    expect(restore.ok()).toBeTruthy();
    ownershipTransferred = false;
  } finally {
    if (ownershipTransferred && organizationId) {
      const newOwner = await api.post(apiPath("/auth/login"), { data: { username: memberUsername, password: memberPassword } });
      if (newOwner.ok()) {
        const newOwnerBody = await newOwner.json();
        const newOwnerHeaders = { Authorization: `Bearer ${newOwnerBody.access_token}` };
        const ownerLogin = await loginOwner(api);
        const originalOwnerMembership = await getMembership(api, organizationId, ownerLogin.user_id, newOwnerHeaders).catch(() => null);
        if (originalOwnerMembership) {
          await api.post(apiPath(`/organizations/${organizationId}/members/${originalOwnerMembership.id}/transfer-owner`), { headers: newOwnerHeaders }).catch(() => undefined);
        }
      }
    }
    await api.dispose();
  }
});

test("Organization browser governance enforces member and suspended-member boundaries", async ({ page, playwright }) => {
  test.setTimeout(60_000);
  const nonce = crypto.randomUUID().replaceAll("-", "").slice(0, 12);
  const memberUsername = `organization_boundary_member_${nonce}`;
  const memberPassword = `OrganizationBoundaryMember!${nonce}`;
  const api: APIRequestContext = await playwright.request.newContext({ baseURL: normalizeApiOrigin(process.env.API_BASE_URL || "http://127.0.0.1:8000/api/v1") });
  try {
    const memberRegister = await api.post(apiPath("/auth/register"), { data: { username: memberUsername, password: memberPassword } });
    expect([200, 201]).toContain(memberRegister.status());
    const memberUser = await memberRegister.json();
    const ownerBody = await loginOwner(api);
    const ownerHeaders = { Authorization: `Bearer ${ownerBody.access_token}` };
    const organization = await getOrganization(api, ownerHeaders, ownerBody.tenant_id);
    const membership = await getMembership(api, organization.id, memberUser.user_id, ownerHeaders);

    await loginInBrowser(page, memberUsername, memberPassword);
    await page.goto(`/organizations/${organization.id}`);
    await expect(page.getByRole("heading", { name: organization.name })).toBeVisible();
    await expect(page.getByRole("button", { name: "添加成员" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "暂停组织" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "转移所有权" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "编辑" })).toHaveCount(0);
    const suspend = await api.patch(apiPath(`/organizations/${organization.id}/members/${membership.id}`), { headers: ownerHeaders, data: { status: "suspended" } });
    expect(suspend.ok()).toBeTruthy();
    await page.reload();
    await expect(page.getByRole("status")).toContainText("组织详情加载失败");
    await expect(page.getByRole("status")).toContainText("当前用户无权访问该组织");
    await expect(page.getByRole("heading", { name: organization.name })).toHaveCount(0);
    const restore = await api.patch(apiPath(`/organizations/${organization.id}/members/${membership.id}`), { headers: ownerHeaders, data: { status: "active" } });
    expect(restore.ok()).toBeTruthy();
  } finally {
    await api.dispose();
  }
});

test("Organization owner transfer exposes owner-only browser controls", async ({ page, playwright }) => {
  test.setTimeout(60_000);
  const nonce = crypto.randomUUID().replaceAll("-", "").slice(0, 12);
  const newOwnerUsername = `organization_transfer_new_${nonce}`;
  const newOwnerPassword = `OrganizationTransferNew!${nonce}`;
  const api: APIRequestContext = await playwright.request.newContext({ baseURL: normalizeApiOrigin(process.env.API_BASE_URL || "http://127.0.0.1:8000/api/v1") });
  let ownershipTransferred = false;
  let organizationId: string | null = null;
  try {
    const ownerBody = await loginOwner(api);
    const ownerHeaders = { Authorization: `Bearer ${ownerBody.access_token}` };
    const organization = await getOrganization(api, ownerHeaders, ownerBody.tenant_id);
    organizationId = organization.id;
    const newRegister = await api.post(apiPath("/auth/register"), { data: { username: newOwnerUsername, password: newOwnerPassword } });
    expect([200, 201]).toContain(newRegister.status());
    const newUser = await newRegister.json();
    const membership = await getMembership(api, organization.id, newUser.user_id, ownerHeaders);
    expect(membership).toMatchObject({ user_id: newUser.user_id, status: "active", role: "member" });
    const transfer = await api.post(apiPath(`/organizations/${organization.id}/members/${membership.id}/transfer-owner`), { headers: ownerHeaders });
    const transferBody = await transfer.text();
    expect(transfer.ok(), `owner transfer failed (${transfer.status()}): ${transferBody}`).toBeTruthy();
    ownershipTransferred = true;

    await loginInBrowser(page, ownerUsername, ownerPassword);
    await page.goto(`/organizations/${organization.id}`);
    await expect(page.getByRole("button", { name: "添加成员" })).toBeVisible();
    await expect(page.getByRole("button", { name: "转移所有权" })).toHaveCount(0);
    await page.evaluate(() => localStorage.clear());
    await loginInBrowser(page, newOwnerUsername, newOwnerPassword);
    await page.goto(`/organizations/${organization.id}`);
    await expect(page.getByRole("button", { name: "添加成员" })).toBeVisible();
    await expect(page.getByRole("button", { name: "转移所有权" }).first()).toBeVisible();

    const newOwner = await api.post(apiPath("/auth/login"), { data: { username: newOwnerUsername, password: newOwnerPassword } });
    expect(newOwner.ok()).toBeTruthy();
    const newOwnerBody = await newOwner.json();
    const newOwnerHeaders = { Authorization: `Bearer ${newOwnerBody.access_token}` };
    const originalOwnerMembership = await getMembership(api, organization.id, ownerBody.user_id, newOwnerHeaders);
    const restore = await api.post(apiPath(`/organizations/${organization.id}/members/${originalOwnerMembership.id}/transfer-owner`), { headers: newOwnerHeaders });
    expect(restore.ok()).toBeTruthy();
    ownershipTransferred = false;
  } finally {
    if (ownershipTransferred && organizationId) {
      const newOwner = await api.post(apiPath("/auth/login"), { data: { username: newOwnerUsername, password: newOwnerPassword } });
      if (newOwner.ok()) {
        const newOwnerBody = await newOwner.json();
        const newOwnerHeaders = { Authorization: `Bearer ${newOwnerBody.access_token}` };
        const ownerLogin = await loginOwner(api);
        const originalOwnerMembership = await getMembership(api, organizationId, ownerLogin.user_id, newOwnerHeaders).catch(() => null);
        if (originalOwnerMembership) {
          await api.post(apiPath(`/organizations/${organizationId}/members/${originalOwnerMembership.id}/transfer-owner`), { headers: newOwnerHeaders }).catch(() => undefined);
        }
      }
    }
    await api.dispose();
  }
});