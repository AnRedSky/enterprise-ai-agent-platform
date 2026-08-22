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
    "el-alert": { template: "<div class=\"alert\"><slot/></div>" }, "el-empty": { template: "<div>empty</div>" },
    "el-dialog": { template: "<div><slot/><slot name=\"footer\"/></div>" }, "el-form": { template: "<form><slot/></form>" },
    "el-form-item": { template: "<div><slot/></div>" }, "el-input": { template: "<input/>" },
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

  it("creates an organization and reloads the list", async () => {
    api.createOrganization.mockResolvedValue({ id: "o2", tenant_id: "t1", name: "New Org", status: "active" });
    const wrapper = mount(Organizations, { global });
    await vi.waitFor(() => expect(api.listOrganizations).toHaveBeenCalled());
    (wrapper.vm as any).name = "New Org";
    await (wrapper.vm as any).create();
    expect(api.createOrganization).toHaveBeenCalledWith({ name: "New Org" });
    expect(api.listOrganizations).toHaveBeenCalledTimes(2);
  });

  it("exposes a loading error without losing the page contract", async () => {
    api.listOrganizations.mockRejectedValueOnce(new Error("Organization API unavailable"));
    const wrapper = mount(Organizations, { global });
    await vi.waitFor(() => expect((wrapper.vm as any).error).toBe("Organization API unavailable"));
  });
});
