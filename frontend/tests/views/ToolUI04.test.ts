import { describe, expect, it, vi, beforeEach } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { ElTable, ElTableColumn, ElTag } from "element-plus";
import ToolWorkbench from "@/views/tools/components/ToolWorkbench.vue";

const mocks = vi.hoisted(() => ({
  listTools: vi.fn(),
  listAgents: vi.fn(),
}));
vi.mock("@/api/tools", () => ({
  listTools: mocks.listTools,
  createTool: vi.fn(),
  enableTool: vi.fn(),
  disableTool: vi.fn(),
  bindTool: vi.fn(),
  unbindTool: vi.fn(),
  executeTool: vi.fn(),
}));
vi.mock("@/api/agents", () => ({ listAgents: mocks.listAgents }));
vi.mock("@/api/auth", () => ({ getRoles: () => ["admin"] }));
vi.mock("@/utils/toolError", () => ({ getToolUserError: vi.fn((_error, fallback) => fallback) }));

const StatePanelStub = {
  name: "StatePanel",
  props: ["state", "title", "description", "actionLabel"],
  emits: ["action"],
  template: `<div class="state-panel" :class="\`state-panel--\${state}\`" role="status"><strong>{{ title }}</strong><span v-if="description">{{ description }}</span><button v-if="actionLabel" @click="$emit('action')">{{ actionLabel }}</button></div>`,
};

function mountView() {
  return mount(ToolWorkbench, {
    global: {
      directives: { loading: () => undefined },
      stubs: {
        StatePanel: StatePanelStub,
        ElTable,
        ElTableColumn,
        ElTag,
        "el-button": { template: "<button @click=\"$emit('click')\"><slot /></button>" },
        "el-alert": true,
        "el-dialog": { template: "<div><slot /><slot name=\"footer\" /></div>" },
        "el-form": { template: "<form><slot /></form>" },
        "el-form-item": { template: "<div><slot /></div>" },
        "el-input": true,
        "el-select": true,
        "el-option": true,
        "el-icon": true,
      },
    },
  });
}

const tool = { id: "t1", name: "天气查询", description: "查询天气", endpoint: null, enabled: true, input_schema: {}, created_at: "2026-08-31T00:00:00Z" };
const agent = { id: "a1", name: "助手", model_id: "m1", status: "published", version: "v1" };

describe("ToolWorkbench UI-04", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mocks.listAgents.mockResolvedValue([agent]);
  });

  it("shows loading while tools and agents are requested", async () => {
    mocks.listTools.mockReturnValueOnce(new Promise(() => undefined));
    const wrapper = mountView();
    await nextTick();
    expect(wrapper.find(".state-panel").classes()).toContain("state-panel--loading");
  });

  it("shows empty state with a create action when no tools are available", async () => {
    mocks.listTools.mockResolvedValueOnce([]);
    const wrapper = mountView();
    await flushPromises();
    const panel = wrapper.find(".state-panel");
    expect(panel.classes()).toContain("state-panel--empty");
    expect(panel.text()).toContain("创建工具");
    expect(panel.find("button").exists()).toBe(true);
  });

  it("shows permission state for a 403 response", async () => {
    mocks.listTools.mockRejectedValueOnce({ response: { status: 403 } });
    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.find(".state-panel").classes()).toContain("state-panel--permission");
    expect(wrapper.text()).toContain("无权查看工具");
  });

  it("shows recoverable error state and retries successfully", async () => {
    mocks.listTools.mockRejectedValueOnce(new Error("network"));
    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.find(".state-panel").classes()).toContain("state-panel--error");
    mocks.listTools.mockResolvedValueOnce([tool]);
    await wrapper.find(".state-panel button").trigger("click");
    await flushPromises();
    expect(mocks.listTools).toHaveBeenCalledTimes(2);
    expect(wrapper.find(".state-panel").exists()).toBe(false);
    expect(wrapper.find(".table").exists()).toBe(true);
  });

  it("renders the existing workspace for populated tools", async () => {
    mocks.listTools.mockResolvedValueOnce([tool]);
    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.find(".state-panel").exists()).toBe(false);
    expect(wrapper.find(".table").exists()).toBe(true);
    expect(wrapper.text()).toContain("共 1 个工具");
  });
});
