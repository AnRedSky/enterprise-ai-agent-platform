import { beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";

const api = vi.hoisted(() => ({
  listAgents: vi.fn(),
  listVersions: vi.fn(),
  getPublishedVersion: vi.fn(),
  createAgent: vi.fn(),
  createVersion: vi.fn(),
  publishAgent: vi.fn(),
  archiveAgent: vi.fn(),
}));
const confirm = vi.hoisted(() => vi.fn());

vi.mock("@/api/agents", () => api);
vi.mock("@/api/chat", () => ({ streamChat: vi.fn() }));
vi.mock("element-plus", () => ({ ElMessage: { success: vi.fn(), error: vi.fn() }, ElMessageBox: { confirm } }));

import AgentWorkbench from "@/views/agents/components/AgentWorkbench.vue";

const agent = { id: "agent-1", name: "企业助手", model_id: "model-1", status: "published", version: "v2" };
const version = { id: "version-3", agent_id: "agent-1", version: "v3", system_prompt: "prompt", model_id: "model-1", knowledge_config: { knowledge_base_ids: [], top_k: 5 }, created_at: "2026-09-02", is_published: false };

function mountView() {
  return mount(AgentWorkbench, { global: { stubs: {
    "el-button": { props: ["loading", "disabled"], template: "<button :disabled=\"disabled\"><slot /></button>" },
    "el-table": { template: "<div><slot /></div>" },
    "el-table-column": { template: "<div><slot :row=\"row\" /></div>", data: () => ({ row: version }) },
    "el-tag": { template: "<span><slot /></span>" },
    "el-alert": { template: "<div><slot /></div>" },
    "el-dialog": { props: ["modelValue"], template: "<div v-if=\"modelValue\"><slot /><slot name=\"footer\" /></div>" },
    "el-form": { template: "<form><slot /></form>" }, "el-form-item": { template: "<div><slot /></div>" }, "el-input": true, "el-divider": true,
    "el-descriptions": { template: "<div><slot /></div>" }, "el-descriptions-item": { template: "<div><slot /></div>" }, "el-scrollbar": { template: "<div><slot /></div>" }, "el-empty": { template: "<div>empty</div>" },
  } } });
}

describe("AgentWorkbench UI-05", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.listAgents.mockResolvedValue([agent]);
    api.listVersions.mockResolvedValue([version]);
    api.getPublishedVersion.mockResolvedValue({ ...version, is_published: true });
    api.createAgent.mockResolvedValue(agent);
    api.createVersion.mockResolvedValue(version);
    api.publishAgent.mockResolvedValue(agent);
    api.archiveAgent.mockResolvedValue({ ...agent, status: "archived" });
    confirm.mockResolvedValue(true);
  });

  it("does not infer or expose a latest-version publish action", async () => {
    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.text()).not.toContain("发布最新版本");
    await (wrapper.vm as any).openVersions(agent);
    await flushPromises();
    expect(wrapper.text()).toContain("v3");
    await (wrapper.vm as any).publishVersion(version);
    expect(api.publishAgent).toHaveBeenCalledWith("agent-1", "version-3");
  });

  it("requires confirmation before archive and refreshes from backend", async () => {
    const wrapper = mountView();
    await flushPromises();
    await (wrapper.vm as any).archive(agent);
    expect(confirm).toHaveBeenCalledTimes(1);
    expect(api.archiveAgent).toHaveBeenCalledWith("agent-1");
    expect(api.listAgents).toHaveBeenCalledTimes(2);
  });

  it("does not call archive when the confirmation is cancelled", async () => {
    confirm.mockRejectedValueOnce("cancel");
    const wrapper = mountView();
    await flushPromises();
    await (wrapper.vm as any).archive(agent);
    expect(api.archiveAgent).not.toHaveBeenCalled();
  });
});