import { describe, expect, it, vi, beforeEach } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import ToolWorkbench from "@/views/tools/components/ToolWorkbench.vue";
import StatePanel from "@/components/ui/StatePanel.vue";

const listTools = vi.fn();
const listAgents = vi.fn();
vi.mock("@/api/tools", () => ({
  listTools,
  createTool: vi.fn(),
  enableTool: vi.fn(),
  disableTool: vi.fn(),
  bindTool: vi.fn(),
  unbindTool: vi.fn(),
  executeTool: vi.fn(),
}));
vi.mock("@/api/agents", () => ({ listAgents }));
vi.mock("@/api/auth", () => ({ getRoles: () => ["admin"] }));
vi.mock("@/utils/toolError", () => ({ getToolUserError: vi.fn((_error, fallback) => fallback) }));
vi.mock("element-plus", () => ({ ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() } }));

function mountView() {
  return mount(ToolWorkbench, { global: { stubs: {
    "el-button": { template: "<button @click=\"$emit('click')\"><slot /></button>" },
    "el-table": { template: "<div class=\"table-stub\"><slot /></div>" },
    "el-table-column": { template: "<div />" },
    "el-tag": true,
    "el-alert": true,
    "el-dialog": { template: "<div><slot /><slot name=\"footer\" /></div>" },
    "el-form": { template: "<form><slot /></form>" },
    "el-form-item": { template: "<div><slot /></div>" },
    "el-input": true,
    "el-select": true,
    "el-option": true,
    "el-icon": true,
  } } });
}

const tool = { id: "t1", name: "天气查询", description: "查询天气", endpoint: null, enabled: true, input_schema: {}, created_at: "2026-08-31T00:00:00Z" };
const agent = { id: "a1", name: "助手", model_id: "m1", status: "published", version: "v1" };

describe("ToolWorkbench UI-04", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listAgents.mockResolvedValue([agent]);
  });

  it("shows loading while tools and agents are requested", async () => {
    listTools.mockReturnValueOnce(new Promise(() => undefined));
    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.findComponent(StatePanel).props("state")).toBe("loading");
  });

  it("shows empty state when no tools are available", async () => {
    listTools.mockResolvedValueOnce([]);
    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.findComponent(StatePanel).props("state")).toBe("empty");
    expect(wrapper.text()).toContain("暂无可用工具");
  });

  it("shows permission state for a 403 response", async () => {
    listTools.mockRejectedValueOnce({ response: { status: 403 } });
    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.findComponent(StatePanel).props("state")).toBe("permission");
    expect(wrapper.text()).toContain("无权查看工具");
  });

  it("shows recoverable error state for non-permission failures", async () => {
    listTools.mockRejectedValueOnce(new Error("network"));
    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.findComponent(StatePanel).props("state")).toBe("error");
    expect(wrapper.text()).toContain("工具加载失败");
  });

  it("renders the existing workspace for populated tools", async () => {
    listTools.mockResolvedValueOnce([tool]);
    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.findComponent(StatePanel).exists()).toBe(false);
    expect(wrapper.find(".table").exists()).toBe(true);
    expect(wrapper.text()).toContain("共 1 个工具");
  });
});
