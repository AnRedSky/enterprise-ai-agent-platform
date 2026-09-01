import { describe, expect, it, vi, beforeEach } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import AgentWorkbench from "@/views/agents/components/AgentWorkbench.vue";
import StatePanel from "@/components/ui/StatePanel.vue";

const api = vi.hoisted(() => ({
  listAgents: vi.fn(),
  listVersions: vi.fn(),
  getPublishedVersion: vi.fn(),
}));
vi.mock("@/api/agents", () => ({
  ...api,
  createAgent: vi.fn(),
  createVersion: vi.fn(),
  publishAgent: vi.fn(),
  archiveAgent: vi.fn(),
}));
vi.mock("@/api/chat", () => ({ streamChat: vi.fn() }));
vi.mock("element-plus", () => ({
  ElMessage: { success: vi.fn(), error: vi.fn() },
  ElMessageBox: { confirm: vi.fn() },
}));

const agentRow = { id: "a1", name: "Agent", model_id: "model", status: "published", version: "v1" };

function mountView() {
  return mount(AgentWorkbench, { global: { stubs: {
    "el-button": { template: "<button @click=\"$emit('click')\"><slot /></button>" },
    "el-table": { template: "<div><slot /></div>" },
    "el-table-column": { template: "<div><slot :row=\"agentRow\" /></div>", data: () => ({ agentRow }) },
    "el-tag": { template: "<span><slot /></span>" }, "el-alert": true,
    "el-dialog": { props: ["modelValue"], template: "<div v-if=\"modelValue\"><slot /><slot name=\"footer\" /></div>" },
    "el-form": { template: "<form><slot /></form>" }, "el-form-item": { template: "<div><slot /></div>" }, "el-input": true, "el-divider": true,
    "el-descriptions": { template: "<div><slot /></div>" }, "el-descriptions-item": { template: "<div><slot /></div>" }, "el-scrollbar": { template: "<div><slot /></div>" }, "el-empty": { template: "<div>empty</div>" },
    "el-icon": { template: "<span><slot /></span>" },
  }, directives: { loading: () => undefined } } });
}

describe("AgentWorkbench UI-04", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it("uses shared loading state while agents are loading", async () => {
    api.listAgents.mockReturnValueOnce(new Promise(() => {}));
    const wrapper = mountView();
    expect(wrapper.findComponent(StatePanel).props("state")).toBe("loading");
  });

  it.each([
    ["empty", [], "暂无智能体"],
    ["error", new Error("network"), "智能体加载失败"],
    ["permission", { response: { status: 403 } }, "无权查看智能体"],
  ] as const)("renders %s agent list state", async (state, response, title) => {
    api.listAgents.mockReturnValueOnce(state === "empty" ? Promise.resolve(response) : Promise.reject(response));
    const wrapper = mountView(); await flushPromises();
    expect(wrapper.findComponent(StatePanel).props("state")).toBe(state);
    expect(wrapper.text()).toContain(title);
  });

  it("renders success state as the populated agent table", async () => {
    api.listAgents.mockResolvedValueOnce([agentRow]);
    const wrapper = mountView(); await flushPromises();
    expect(wrapper.findComponent(StatePanel).exists()).toBe(false);
    expect(wrapper.find(".table").exists()).toBe(true);
  });

  it("separates chat context permission from chat context error", async () => {
    api.listAgents.mockResolvedValueOnce([agentRow]);
    api.getPublishedVersion.mockRejectedValueOnce({ response: { status: 403 } });
    const wrapper = mountView(); await flushPromises();
    const button = wrapper.findAll("button").find((node) => node.text() === "对话调试");
    expect(button).toBeDefined();
    await button!.trigger("click");
    await vi.waitFor(() => expect((wrapper.vm as any).chatContextState).toBe("permission"));
    expect(api.getPublishedVersion).toHaveBeenCalledWith("a1");
    expect(wrapper.text()).toContain("无权加载调试配置");
  });
});
