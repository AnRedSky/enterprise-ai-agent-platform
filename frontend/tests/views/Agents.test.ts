import { describe, expect, it, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";

const api = vi.hoisted(() => ({
  listAgents: vi.fn(), listVersions: vi.fn(), createAgent: vi.fn(), createVersion: vi.fn(), publishAgent: vi.fn(), archiveAgent: vi.fn(),
}));
vi.mock("../../src/api/agents", () => ({ ...api }));
vi.mock("../../src/api/chat", () => ({ streamChat: vi.fn() }));
vi.mock("element-plus", () => ({ ElMessage: { success: vi.fn(), error: vi.fn() }, ElMessageBox: { confirm: vi.fn() } }));

import Agents from "../../src/views/agents/components/AgentWorkbench.vue";

const stubs = {
  "el-button": { props: ["disabled", "loading"], template: "<button :disabled=\"disabled\"><slot/></button>" },
  "el-table": { template: "<div><slot/></div>" }, "el-table-column": { template: "<div/>" },
  "el-alert": { template: "<div class=\"alert\"><slot/></div>" }, "el-empty": { template: "<div>empty</div>" },
  "el-dialog": { props: ["modelValue"], template: "<div><slot/><slot name=\"footer\"/></div>" },
  "el-form": { template: "<form><slot/></form>" }, "el-form-item": { template: "<div><slot/></div>" },
  "el-input": { template: "<input/>" }, "el-divider": { template: "<hr/>" }, "el-scrollbar": { template: "<div><slot/></div>" },
};
const global = { stubs, directives: { loading: () => undefined } };

const agent = { id: "a1", name: "助手", description: "", model_id: "mock-model", version: "1.0.0", status: "published", published_version_id: "v1", created_at: "2026-01-01" };
const versions = [
  { id: "v2", agent_id: "a1", version: "1.1.0", system_prompt: "new", model_id: "mock-model", created_at: "2026-01-02", is_published: false },
  { id: "v1", agent_id: "a1", version: "1.0.0", system_prompt: "old", model_id: "mock-model", created_at: "2026-01-01", is_published: true },
];

describe("AgentWorkbench lifecycle", () => {
  beforeEach(() => { vi.clearAllMocks(); api.listAgents.mockResolvedValue([agent]); api.listVersions.mockResolvedValue(versions); });

  it("loads agents and opens versions", async () => {
    const wrapper = mount(Agents, { global });
    await vi.waitFor(() => expect(api.listAgents).toHaveBeenCalled());
    await (wrapper.vm as any).openVersions(agent);
    expect(api.listVersions).toHaveBeenCalledWith("a1");
    expect((wrapper.vm as any).versions[0].is_published).toBe(false);
  });

  it("publishes a selected draft version and refreshes lifecycle state", async () => {
    api.publishAgent.mockResolvedValue({ ...agent, version: "1.1.0", published_version_id: "v2" });
    const wrapper = mount(Agents, { global });
    await vi.waitFor(() => expect(api.listAgents).toHaveBeenCalled());
    await (wrapper.vm as any).openVersions(agent);
    await (wrapper.vm as any).publishVersion(versions[0]);
    expect(api.publishAgent).toHaveBeenCalledWith("a1", "v2");
    expect(api.listAgents).toHaveBeenCalledTimes(2);
  });

  it("does not allow creating a version for archived agents", async () => {
    const archived = { ...agent, status: "archived", version: null, published_version_id: null };
    const wrapper = mount(Agents, { global });
    await (wrapper.vm as any).openVersions(archived);
    (wrapper.vm as any).versionForm.system_prompt = "new prompt";
    await (wrapper.vm as any).createVersion();
    expect(api.createVersion).not.toHaveBeenCalled();
  });
});
