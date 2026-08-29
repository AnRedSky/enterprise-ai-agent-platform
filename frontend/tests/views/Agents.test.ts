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
  "el-tag": { template: "<span><slot/></span>" },
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

  it("uses Chinese-only visible Agent terminology while preserving technical identifiers", async () => {
    const wrapper = mount(Agents, { global });
    await vi.waitFor(() => expect(api.listAgents).toHaveBeenCalled());
    const text = wrapper.text();
    expect(text).toContain("智能体工作台");
    expect(text).toContain("创建智能体");
    expect(text).toContain("对话调试");
    expect(text).toContain("系统提示词");
    expect(text).not.toContain("Agent 工作台");
    expect(text).not.toContain("创建 Agent");
    expect(text).not.toContain("Published");
    expect(text).not.toContain("System Prompt");
    expect(text).not.toContain("Chat");
  });

  it("maps agent lifecycle status to Chinese while keeping the backend value", async () => {
    const wrapper = mount(Agents, { global });
    await vi.waitFor(() => expect(api.listAgents).toHaveBeenCalled());
    expect((wrapper.vm as any).statusLabel("published")).toBe("已发布");
    expect((wrapper.vm as any).statusLabel("draft")).toBe("草稿");
    expect((wrapper.vm as any).statusLabel("archived")).toBe("已归档");
    expect((wrapper.vm as any).statusLabel("unknown_status")).toBe("未知状态（unknown_status）");
    expect(agent.status).toBe("published");
  });

  it("uses Chinese labels for runtime identifiers", async () => {
    const wrapper = mount(Agents, { global });
    await vi.waitFor(() => expect(api.listAgents).toHaveBeenCalled());
    (wrapper.vm as any).openChat(agent);
    (wrapper.vm as any).requestId = "request-123456789";
    (wrapper.vm as any).traceId = "trace-123456789";
    (wrapper.vm as any).sessionId = "session-123456789";
    (wrapper.vm as any).executionId = "execution-123456789";
    await wrapper.vm.$nextTick();
    const text = wrapper.text();
    expect(text).toContain("请求标识");
    expect(text).toContain("链路追踪标识");
    expect(text).toContain("会话标识");
    expect(text).toContain("执行标识");
    expect(text).not.toContain("请求 ID");
    expect(text).not.toContain("链路追踪 ID");
    expect(text).not.toContain("会话 ID");
    expect(text).not.toContain("执行 ID");
  });

  it("hides raw HTTP error text from the user-facing error area", async () => {
    api.listAgents.mockRejectedValue(new Error("500 Internal Server Error"));
    const wrapper = mount(Agents, { global });
    await vi.waitFor(() => expect(wrapper.text()).toContain("智能体列表加载失败，请刷新后重试"));
    expect(wrapper.text()).not.toContain("500 Internal Server Error");
  });
});
