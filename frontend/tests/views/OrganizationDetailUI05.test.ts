import { beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";

const api = vi.hoisted(() => ({ getOrganization: vi.fn(), listMembers: vi.fn(), addMember: vi.fn(), updateMember: vi.fn(), removeMember: vi.fn(), transferOwner: vi.fn(), updateOrganization: vi.fn(), getUserId: vi.fn(), confirm: vi.fn(), push: vi.fn() }));
vi.mock("@/api/organizations", () => ({ getOrganization: api.getOrganization, listMembers: api.listMembers, addMember: api.addMember, updateMember: api.updateMember, removeMember: api.removeMember, transferOwner: api.transferOwner, updateOrganization: api.updateOrganization }));
vi.mock("@/api/auth", () => ({ getUserId: api.getUserId }));
vi.mock("vue-router", () => ({ useRoute: () => ({ params: { id: "org-1" } }), useRouter: () => ({ push: api.push }) }));
vi.mock("element-plus", () => ({ ElMessage: { success: vi.fn(), error: vi.fn() }, ElMessageBox: { confirm: api.confirm } }));

import OrganizationDetail from "@/views/organizations/detail.vue";

const organization = { id: "org-1", tenant_id: "tenant-1", name: "总部", status: "active" };
const owner = { id: "membership-1", organization_id: "org-1", user_id: "user-1", status: "active", role: "owner" as const };
const member = { id: "membership-2", organization_id: "org-1", user_id: "user-2", status: "active", role: "member" as const };
const global = { stubs: {
  PageHeader: { template: "<header><slot name=\"actions\" /></header>" }, SurfaceCard: { template: "<section><slot name=\"header\" /><slot /></section>" }, StatePanel: { props: ["state", "title"], template: "<div class=\"state-panel\">{{ state }} {{ title }}</div>" },
  "el-button": { props: ["loading", "disabled"], template: "<button :disabled=\"disabled\" @click=\"$emit('click')\"><slot /></button>" }, "el-table": { template: "<div><slot /></div>" }, "el-table-column": { template: "<div />" }, "el-tag": { template: "<span><slot /></span>" }, "el-dialog": { props: ["modelValue"], template: "<div v-if=\"modelValue\"><slot /><slot name=\"footer\" /></div>" }, "el-form": { template: "<form><slot /></form>" }, "el-form-item": { template: "<div><slot /></div>" }, "el-input": { template: "<input />" }, "el-select": { template: "<select><slot /></select>" }, "el-option": { template: "<option><slot /></option>" }, "el-pagination": { template: "<div />" },
} };

describe("Organization detail UI-05", () => {
  beforeEach(() => { vi.clearAllMocks(); api.getUserId.mockReturnValue("user-1"); api.getOrganization.mockResolvedValue(organization); api.listMembers.mockResolvedValue({ items: [owner, member], total: 2 }); api.confirm.mockResolvedValue(true); api.updateMember.mockResolvedValue(member); api.removeMember.mockResolvedValue(undefined); api.transferOwner.mockResolvedValue(member); api.updateOrganization.mockResolvedValue({ ...organization, status: "suspended" }); });

  it("renders organization detail with shared surface/state patterns", async () => {
    const wrapper = mount(OrganizationDetail, { global }); await flushPromises();
    expect(wrapper.find("header").exists()).toBe(true);
    expect(wrapper.findAll("section").length).toBeGreaterThanOrEqual(2);
  });

  it("renders shared error state for organization permission failure", async () => {
    api.getOrganization.mockRejectedValueOnce({ response: { status: 403 } });
    const wrapper = mount(OrganizationDetail, { global }); await flushPromises();
    expect(wrapper.find(".state-panel").text()).toContain("error");
    expect(wrapper.text()).toContain("组织详情加载失败");
  });

  it("updates member using explicit membership id after confirmation", async () => {
    const wrapper = mount(OrganizationDetail, { global }); await flushPromises();
    await (wrapper.vm as any).toggleMember(member);
    expect(api.confirm).toHaveBeenCalledTimes(1);
    expect(api.updateMember).toHaveBeenCalledWith("org-1", "membership-2", { status: "suspended" });
  });

  it("does not mutate the owner through member actions", async () => {
    const wrapper = mount(OrganizationDetail, { global }); await flushPromises();
    await (wrapper.vm as any).toggleMember(owner);
    await (wrapper.vm as any).remove(owner);
    expect(api.updateMember).not.toHaveBeenCalled();
    expect(api.removeMember).not.toHaveBeenCalled();
  });
});
