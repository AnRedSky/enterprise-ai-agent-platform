import { beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";

const api = vi.hoisted(() => ({ getOrganization: vi.fn(), listMembers: vi.fn(), addMember: vi.fn(), updateMember: vi.fn(), removeMember: vi.fn(), transferOwner: vi.fn(), updateOrganization: vi.fn() }));
vi.mock("../../src/api/organizations", () => ({ ...api }));
vi.mock("../../src/api/auth", () => ({ getUserId: vi.fn(() => "u1") }));
vi.mock("vue-router", () => ({ useRoute: () => ({ params: { id: "o1" } }), useRouter: () => ({ push: vi.fn() }) }));
vi.mock("element-plus", () => ({ ElMessage: { success: vi.fn(), error: vi.fn() }, ElMessageBox: { confirm: vi.fn().mockResolvedValue(true) } }));

import OrganizationDetail from "../../src/views/organizations/detail.vue";

const global = {
  stubs: {
    "el-button": { template: "<button @click=\"$emit('click')\"><slot/></button>" }, "el-card": { template: "<div><slot/><slot name=\"header\"/></div>" },
    "el-alert": { template: "<div><slot/></div>" }, "el-table": { template: "<div><slot/></div>" }, "el-table-column": { template: "<div/>" },
    "el-tag": { template: "<span><slot/></span>" }, "el-empty": { template: "<div>empty</div>" }, "el-dialog": { template: "<div><slot/><slot name=\"footer\"/></div>" },
    "el-form": { template: "<form><slot/></form>" }, "el-form-item": { template: "<div><slot/></div>" }, "el-input": { template: "<input/>" },
    "el-select": { template: "<select><slot/></select>" }, "el-option": { template: "<option><slot/></option>" },
  }, directives: { loading: () => undefined },
};

const organization = { id: "o1", tenant_id: "t1", name: "Acme", status: "active" as const };
const owner = { id: "m1", organization_id: "o1", user_id: "u1", status: "active" as const, role: "owner" as const };
const admin = { id: "m2", organization_id: "o1", user_id: "u2", status: "active" as const, role: "admin" as const };
const member = { id: "m3", organization_id: "o1", user_id: "u3", status: "active" as const, role: "member" as const };

describe("OrganizationDetail management UI", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    const { getUserId } = await import("../../src/api/auth");
    vi.mocked(getUserId).mockReturnValue("u1");
    api.getOrganization.mockResolvedValue(organization);
    api.listMembers.mockResolvedValue({ items: [owner, admin, member], total: 3 });
  });

  it("loads organization and membership state", async () => {
    const wrapper = mount(OrganizationDetail, { global });
    await vi.waitFor(() => expect(api.listMembers).toHaveBeenCalledWith("o1"));
    expect((wrapper.vm as any).organization.name).toBe("Acme");
    expect((wrapper.vm as any).members).toHaveLength(3);
    expect((wrapper.vm as any).canManage).toBe(true);
    expect((wrapper.vm as any).canTransferOwner).toBe(true);
  });

  it("uses the dedicated owner transfer contract", async () => {
    api.transferOwner.mockResolvedValue({ ...admin, role: "owner" });
    const wrapper = mount(OrganizationDetail, { global });
    await vi.waitFor(() => expect(api.listMembers).toHaveBeenCalled());
    await (wrapper.vm as any).transfer(admin);
    expect(api.transferOwner).toHaveBeenCalledWith("o1", "m2");
  });

  it("supports member lifecycle actions through the backend contract", async () => {
    const wrapper = mount(OrganizationDetail, { global });
    await vi.waitFor(() => expect(api.listMembers).toHaveBeenCalled());
    await (wrapper.vm as any).toggleMember(member);
    expect(api.updateMember).toHaveBeenCalledWith("o1", "m3", { status: "suspended" });
    await (wrapper.vm as any).remove(member);
    expect(api.removeMember).toHaveBeenCalledWith("o1", "m3");
  });

  it("does not expose owner editing as a normal role update", async () => {
    const wrapper = mount(OrganizationDetail, { global });
    await vi.waitFor(() => expect(api.listMembers).toHaveBeenCalled());
    expect((wrapper.vm as any).members.find((m: any) => m.role === "owner").role).toBe("owner");
    expect(api.updateMember).not.toHaveBeenCalled();
  });

  it("does not expose management controls to a member", async () => {
    const { getUserId } = await import("../../src/api/auth");
    vi.mocked(getUserId).mockReturnValue("u3");
    const wrapper = mount(OrganizationDetail, { global });
    await vi.waitFor(() => expect(api.listMembers).toHaveBeenCalled());
    expect((wrapper.vm as any).canManage).toBe(false);
    expect((wrapper.vm as any).canTransferOwner).toBe(false);
  });

  it("keeps owner transfer exclusive to the owner after transfer", async () => {
    const { getUserId } = await import("../../src/api/auth");
    vi.mocked(getUserId).mockReturnValue("u1");
    api.listMembers.mockResolvedValue({ items: [{ ...owner, role: "admin" }, { ...admin, role: "owner" }, member], total: 3 });
    const previousOwner = mount(OrganizationDetail, { global });
    await vi.waitFor(() => expect(api.listMembers).toHaveBeenCalled());
    expect((previousOwner.vm as any).canManage).toBe(true);
    expect((previousOwner.vm as any).canTransferOwner).toBe(false);

    vi.mocked(getUserId).mockReturnValue("u2");
    const newOwner = mount(OrganizationDetail, { global });
    await vi.waitFor(() => expect(api.listMembers).toHaveBeenCalledTimes(2));
    expect((newOwner.vm as any).canManage).toBe(true);
    expect((newOwner.vm as any).canTransferOwner).toBe(true);
  });
});
