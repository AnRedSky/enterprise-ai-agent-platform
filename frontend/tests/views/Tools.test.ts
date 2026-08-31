import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ToolWorkbench from "@/views/tools/components/ToolWorkbench.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import PageToolbar from "@/components/ui/PageToolbar.vue";
import SurfaceCard from "@/components/ui/SurfaceCard.vue";
import StatePanel from "@/components/ui/StatePanel.vue";

const api = vi.hoisted(() => ({ listTools: vi.fn(), listAgents: vi.fn() }));
vi.mock("@/api/auth", () => ({ getRoles: () => ["admin"] }));
vi.mock("@/api/agents", () => ({ listAgents: api.listAgents }));
vi.mock("@/api/tools", () => ({ bindTool: vi.fn(), createTool: vi.fn(), disableTool: vi.fn(), enableTool: vi.fn(), executeTool: vi.fn(), listTools: api.listTools, unbindTool: vi.fn() }));
vi.mock("@/utils/toolError", () => ({ getToolUserError: (_error: unknown, fallback: string) => fallback }));

function mountPage() {
  return mount(ToolWorkbench, { global: { stubs: {
    "el-button": { template: "<button><slot /></button>" }, "el-alert": true, "el-table": true, "el-table-column": true, "el-empty": true, "el-dialog": true,
    "el-form": true, "el-form-item": true, "el-input": true, "el-select": true, "el-option": true, "el-tag": true,
  } } });
}

describe("ToolWorkbench UI-03 migration", () => {
  beforeEach(() => { api.listTools.mockResolvedValue([]); api.listAgents.mockResolvedValue([]); });
  it("uses shared PageHeader, PageToolbar and SurfaceCard patterns", async () => {
    api.listTools.mockResolvedValue([{ id: "t1", name: "Tool", description: "test", enabled: true }]);
    const wrapper = mountPage(); await flushPromises();
    expect(wrapper.findComponent(PageHeader).exists()).toBe(true);
    expect(wrapper.findComponent(PageToolbar).exists()).toBe(true);
    expect(wrapper.findComponent(SurfaceCard).exists()).toBe(true);
    expect(wrapper.findComponent(PageHeader).props("title")).toBe("工具管理");
    expect(wrapper.findComponent(PageToolbar).props("title")).toBe("工具列表");
  });
  it("renders the shared empty-state contract when no tools are returned", async () => {
    const wrapper = mountPage(); await flushPromises();
    const state = wrapper.findComponent(StatePanel);
    expect(state.exists()).toBe(true);
    expect(state.props("state")).toBe("empty");
    expect(state.props("title")).toBe("暂无可用工具");
    expect(state.props("description")).toBe("当前没有可用工具，请创建工具或启用已有工具。");
  });
  it("keeps the administrator creation action in the PageHeader action slot", async () => {
    const wrapper = mountPage(); await flushPromises();
    const header = wrapper.findComponent(PageHeader);
    expect(header.text()).toContain("创建工具");
  });
});
