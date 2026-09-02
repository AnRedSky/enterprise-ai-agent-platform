import { beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";

const api = vi.hoisted(() => ({ listOrganizations: vi.fn(), createOrganization: vi.fn() }));
vi.mock("@/api/organizations", () => ({ ...api }));
vi.mock("element-plus", () => ({ ElMessage: { success: vi.fn(), error: vi.fn() } }));

import Organizations from "@/views/organizations/index.vue";

const global = { stubs: {
  PageHeader: { template: "<header><slot name=\"actions\" /></header>" },
  SurfaceCard: { template: "<section class=\"surface-card\"><slot /></section>" },
  StatePanel: { props: ["state", "title", "description"], template: "<div class=\"state-panel\">{{ state }} {{ title }} {{ description }}</div>" },
  "el-button": { props: ["loading", "disabled"], template: "<button :disabled=\"disabled\"><slot /></button>" },
  "el-table": { template: "<div><slot /></div>" }, "el-table-column": { template: "<div />" }, "el-tag": { template: "<span><slot /></span>" },
  "el-dialog": { props: ["modelValue"], template: "<div v-if=\"modelValue\"><slot /><slot name=\"footer\" /></div>" }, "el-form": { template: "<form><slot /></form>" }, "el-form-item": { template: "<div><slot /></div>" }, "el-input": { template: "<input />" },
} };

describe("Organizations UI-03/UI-04/UI-05", () => {
  beforeEach(() => { vi.clearAllMocks(); api.listOrganizations.mockResolvedValue({ items: [{ id: "org-1", tenant_id: "tenant-1", name: "总部", status: "active" }], total: 1 }); api.createOrganization.mockResolvedValue({ id: "org-2", tenant_id: "tenant-1", name: "研发部", status: "active" }); });

  it("renders shared page header and surface card for the organization list", async () => {
    const wrapper = mount(Organizations, { global }); await flushPromises();
    expect(wrapper.find("header").exists()).toBe(true);
    expect(wrapper.find(".surface-card").exists()).toBe(true);
  });

  it.each([
    ["empty", [], "暂无组织"],
    ["error", new Error("network"), "组织列表加载失败"],
    ["permission", { response: { status: 403 } }, "无权访问组织"],
  ] as const)("renders %s organization list state", async (state, response, title) => {
    api.listOrganizations.mockImplementationOnce(state === "empty" ? () => Promise.resolve({ items: [], total: 0 }) : () => Promise.reject(response));
    const wrapper = mount(Organizations, { global }); await flushPromises();
    expect(wrapper.find(".state-panel").text()).toContain(state);
    expect(wrapper.text()).toContain(title);
  });

  it("creates with the backend contract and refreshes from backend", async () => {
    const wrapper = mount(Organizations, { global }); await flushPromises();
    (wrapper.vm as any).name = "研发部";
    await (wrapper.vm as any).create();
    expect(api.createOrganization).toHaveBeenCalledWith({ name: "研发部" });
    expect(api.listOrganizations).toHaveBeenCalledTimes(2);
  });
});
