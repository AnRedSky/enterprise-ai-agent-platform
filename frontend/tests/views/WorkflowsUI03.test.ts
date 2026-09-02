import { beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";

const api = vi.hoisted(() => ({ list: vi.fn() }));
vi.mock("../../src/api/workflows", () => ({
  workflowApi: api,
}));
vi.mock("element-plus", () => ({
  ElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn() },
  ElMessageBox: { confirm: vi.fn(), prompt: vi.fn() },
}));

import Workflows from "../../src/views/workflows/index.vue";

const global = {
  stubs: {
    PageHeader: { template: "<header class=\"page-header\"><slot name=\"actions\"/></header>" },
    SurfaceCard: { props: ["title", "description"], template: "<section class=\"surface-card\"><slot name=\"header\"/><slot/></section>" },
    StatePanel: { props: ["state", "title", "description", "actionLabel"], emits: ["action"], template: "<div class=\"state-panel\">{{ state }} {{ title }} {{ description }}</div>" },
    "el-button": { template: "<button><slot/></button>" },
    "el-form": { template: "<form><slot/></form>" },
    "el-form-item": { template: "<div><slot/></div>" },
    "el-input": { template: "<input />" },
    "el-divider": { template: "<hr />" },
    "el-row": { template: "<div><slot/></div>" },
    "el-col": { template: "<div><slot/></div>" },
    "el-table": { template: "<div><slot/></div>" },
    "el-table-column": { template: "<div />" },
  },
};

describe("Workflows UI-03", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.list.mockResolvedValue({ data: [] });
  });

  it("uses the shared page header and surface card for the workflow page", async () => {
    const wrapper = mount(Workflows, { global });
    await vi.waitFor(() => expect(api.list).toHaveBeenCalledTimes(1));
    expect(wrapper.find(".page-header").exists()).toBe(true);
    expect(wrapper.findAll(".surface-card").length).toBe(1);
  });

  it("keeps the workflow list empty state on the shared StatePanel pattern", async () => {
    const wrapper = mount(Workflows, { global });
    await vi.waitFor(() => expect(wrapper.text()).toContain("暂无工作流"));
    expect(wrapper.text()).toContain("empty");
  });
});
