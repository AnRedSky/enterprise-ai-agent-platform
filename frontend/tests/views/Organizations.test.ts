import { beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";

const api = vi.hoisted(() => ({ listOrganizations: vi.fn(), createOrganization: vi.fn() }));
vi.mock("../../src/api/organizations", () => ({ ...api }));
vi.mock("element-plus", () => ({ ElMessage: { success: vi.fn(), error: vi.fn() } }));

import Organizations from "../../src/views/organizations/index.vue";

const global = {
  stubs: {
    "el-button": { template: "<button @click=\"$emit('click')\"><slot/></button>" },
    "el-table": { template: "<div><slot/></div>" }, "el-table-column": { template: "<div/>" },
    "el-alert": { props: ["title"], template: "<div class=\"alert\">{{ title }}</div>" }, "el-empty": { template: "<div>empty</div>" },
    "el-dialog": { template: "<div><slot/><slot name=\"footer\"/></div>" }, "el-form": { template: "<form><slot/></form>" },
    "el-form-item": { template: "<div><slot/></div>" }, "el-input": { template: "<input/>" }, "el-tag": { template: "<span><slot/></span>" },
    "router-link": { template: "<a><slot/></a>" },
  }, directives: { loading: () => undefined },
};

describe("Organizations management UI", () => {
  beforeEach(() => { vi.clearAllMocks(); api.listOrganizations.mockResolvedValue({ items: [{ id: "o1", tenant_id: "t1", name: "Acme", status: "active" }], total: 1 }); });

  it("loads the real organization contract into the view", async () => {
    const wrapper = mount(Organizations, { global });
    await vi.waitFor(() => expect(api.listOrganizations).toHaveBeenCalledWith());
    expect((wrapper.vm as any).organizations[0].name).toBe("Acme");
  });

  it("uses Chinese wording while preserving technical identifiers", async () => {
    const wrapper = mount(Organizations, { global });
    await vi.waitFor(() => expect(api.listOrganizations).toHaveBeenCalled());
    const text = wrapper.text();
    expect(text).toContain("组织");
    expect(text).toContain("创建组织");
    expect(text).toContain("管理成员");
    expect(text).not.toContain("Organizations");
    expect(text).not.toContain("Organization");
  });

  it("maps organization status to Chinese with a safe unknown fallback", async () => {
    const wrapper = mount(Organizations, { global });
    await vi.waitFor(() => expect(api.listOrganizations).toHaveBeenCalled());
    expect((wrapper.vm as any).statusLabel("active")).toBe("已启用");
    expect((wrapper.vm as any).statusLabel("pending")).toBe("待处理");
    expect((wrapper.vm as any).statusLabel("unknown_status")).toBe("未知状态（unknown_status）");
  });

  it("creates an organization and reloads the list", async () => {
    api.createOrganization.mockResolvedValue({ id: "o2", tenant_id: "t1", name: "New Org", status: "active" });
    const wrapper = mount(Organizations, { global });
    await vi.waitFor(() => expect(api.listOrganizations).toHaveBeenCalled());
    (wrapper.vm as any).name = "New Org";
    await (wrapper.vm as any).create();
    expect(api.createOrganization).toHaveBeenCalledWith({ name: "New Org" });
    expect(api.listOrganizations).toHaveBeenCalledTimes(2);
  });

  it("replaces raw API HTTP errors with a Chinese user-facing message", async () => {
    api.listOrganizations.mockRejectedValueOnce(new Error("500 Internal Server Error"));
    const wrapper = mount(Organizations, { global });
    await vi.waitFor(() => expect((wrapper.vm as any).error).toBe("组织列表加载失败，请稍后重试"));
    expect(wrapper.text()).not.toContain("500 Internal Server Error");
  });
});
