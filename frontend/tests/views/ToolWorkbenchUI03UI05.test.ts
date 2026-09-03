import { beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { nextTick } from "vue";

const api = vi.hoisted(() => ({ listTools: vi.fn(), createTool: vi.fn(), enableTool: vi.fn(), disableTool: vi.fn(), bindTool: vi.fn(), unbindTool: vi.fn(), executeTool: vi.fn(), listAgents: vi.fn(), getRoles: vi.fn(), confirm: vi.fn() }));
vi.mock("@/api/tools", () => ({ listTools: api.listTools, createTool: api.createTool, enableTool: api.enableTool, disableTool: api.disableTool, bindTool: api.bindTool, unbindTool: api.unbindTool, executeTool: api.executeTool }));
vi.mock("@/api/agents", () => ({ listAgents: api.listAgents }));
vi.mock("@/api/auth", () => ({ getRoles: api.getRoles }));
vi.mock("element-plus", () => ({ ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() } }));
vi.mock("@/utils/toolError", () => ({ getToolUserError: (_e: unknown, fallback: string) => fallback }));

import ToolWorkbench from "@/views/tools/components/ToolWorkbench.vue";

const tool = { id: "tool-1", name: "订单查询", description: "查询订单", endpoint: null, enabled: true, input_schema: {}, created_at: "2026-09-02" };
const agent = { id: "agent-1", name: "企业助手", model_id: "model-1", status: "published", version: "v1" };
const global = { stubs: {
  PageHeader: { template: "<header><slot name=\"actions\" /></header>" },
  PageToolbar: { template: "<div><slot /></div>" },
  SurfaceCard: { template: "<section><slot name=\"header\" /><slot /></section>" },
  StatePanel: { props: ["state", "title"], template: "<div class=\"state-panel\">{{ state }} {{ title }}</div>" },
  ConfirmDialog: { props: ["modelValue", "loading"], template: `<div v-if="modelValue"><button @click="$emit('confirm')">确认</button><button @click="$emit('cancel')">取消</button></div>` },
  "el-button": { props: ["loading", "disabled"], template: "<button :disabled=\"disabled\" @click=\"$emit('click')\"><slot /></button>" },
  "el-table": { template: "<div><slot /></div>" }, "el-table-column": { template: "<div />" },
  "el-dialog": { props: ["modelValue"], template: "<div v-if=\"modelValue\"><slot /><slot name=\"footer\" /></div>" },
  "el-form": { template: "<form><slot /></form>" }, "el-form-item": { template: "<div><slot /></div>" }, "el-input": { template: "<input />" },
  "el-select": { template: "<select><slot /></select>" }, "el-option": { template: "<option><slot /></option>" }, "el-alert": { template: "<div><slot /></div>" }, "el-tag": { template: "<span><slot /></span>" },
} };

describe("ToolWorkbench UI-03/UI-05", () => {
  beforeEach(() => { vi.clearAllMocks(); api.getRoles.mockReturnValue(["admin"]); api.listTools.mockResolvedValue([tool]); api.listAgents.mockResolvedValue([agent]); });

  it("uses shared loading and empty/error state patterns", async () => {
    api.listTools.mockReturnValueOnce(new Promise(() => {}));
    const loading = mount(ToolWorkbench, { global });
    await nextTick();
    expect(loading.find(".state-panel").text()).toContain("loading");

    api.listTools.mockRejectedValueOnce(new Error("network"));
    const error = mount(ToolWorkbench, { global }); await flushPromises();
    expect(error.find(".state-panel").text()).toContain("error");
  });

  it("keeps tool actions bound to explicit backend ids", async () => {
    const wrapper = mount(ToolWorkbench, { global }); await flushPromises();
    await (wrapper.vm as any).openExecute(tool);
    expect((wrapper.vm as any).selectedTool.id).toBe("tool-1");
    (wrapper.vm as any).selectedAgent = "agent-1";
    (wrapper.vm as any).argumentsText = "{}";
    api.executeTool.mockResolvedValueOnce({ execution_id: "exec-1", status: "completed" });
    await (wrapper.vm as any).execute();
    expect(api.executeTool).toHaveBeenCalledWith("tool-1", "agent-1", {});
  });

  it("uses confirmation before enable/disable and refreshes after success", async () => {
    const wrapper = mount(ToolWorkbench, { global }); await flushPromises();
    (wrapper.vm as any).requestToggle(tool);
    expect((wrapper.vm as any).confirmVisible).toBe(true);
    await (wrapper.vm as any).confirmAction();
    expect(api.disableTool).toHaveBeenCalledWith("tool-1");
    expect(api.listTools).toHaveBeenCalledTimes(2);
  });
});
