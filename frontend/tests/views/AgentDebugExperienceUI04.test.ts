import { beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
const api = vi.hoisted(() => ({ listAgents: vi.fn(), getPublishedVersion: vi.fn() }));
vi.mock("../../src/api/agents", () => ({ ...api }));
vi.mock("element-plus", () => ({ ElMessage: { error: vi.fn() } }));
import AgentDebugExperience from "../../src/views/agents/components/AgentDebugExperience.vue";
const global = { stubs: { SurfaceCard: { template: "<section><slot name=\"header\"/><slot/></section>" }, StatePanel: { props: ["state", "title", "description", "actionLabel"], emits: ["action"], template: "<div class=\"state-panel\">{{ state }} {{ title }} {{ description }}</div>" }, "el-tag": { template: "<span><slot/></span>" }, "el-button": { template: "<button @click=\"$emit('click')\"><slot/></button>" }, "el-select": { props: ["modelValue"], template: "<select><slot/></select>" }, "el-option": { template: "<option><slot/></option>" } } };
const agent = { id: "a1", name: "助手", description: "", model_id: "model-1", version: "1.0.0", status: "published", published_version_id: "v1", created_at: "2026-01-01" };
const version = { id: "v1", agent_id: "a1", version: "1.0.0", system_prompt: "help", model_id: "model-1", created_at: "2026-01-01", is_published: true };
describe("AgentDebugExperience UI-04", () => {
  beforeEach(() => { vi.clearAllMocks(); api.listAgents.mockResolvedValue([agent]); api.getPublishedVersion.mockResolvedValue(version); });
  it("renders the loading state while the debug context is loading", async () => { let resolve!: (value: typeof agent[]) => void; api.listAgents.mockReturnValue(new Promise((r) => { resolve = r; })); const wrapper = mount(AgentDebugExperience, { global }); await vi.waitFor(() => expect(wrapper.text()).toContain("loading")); expect(wrapper.text()).toContain("正在加载调试上下文"); resolve([agent]); await vi.waitFor(() => expect(wrapper.text()).toContain("当前生效版本")); });
  it("renders the empty state when no accessible agent exists", async () => { api.listAgents.mockResolvedValue([]); const wrapper = mount(AgentDebugExperience, { global }); await vi.waitFor(() => expect(wrapper.text()).toContain("暂无可调试智能体")); expect(api.getPublishedVersion).not.toHaveBeenCalled(); });
  it("renders the shared error state and does not expose raw backend errors", async () => { api.listAgents.mockRejectedValue(new Error("500 Internal Server Error")); const wrapper = mount(AgentDebugExperience, { global }); await vi.waitFor(() => expect(wrapper.text()).toContain("调试上下文加载失败")); expect(wrapper.text()).not.toContain("500 Internal Server Error"); });
});
