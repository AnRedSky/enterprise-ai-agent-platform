import { describe, expect, it, vi, beforeEach } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { ElTable, ElTableColumn, ElTag } from "element-plus";
import KnowledgeWorkbench from "@/views/knowledge/components/KnowledgeWorkbench.vue";

const mocks = vi.hoisted(() => ({ listKnowledgeBases: vi.fn() }));
vi.mock("@/api/knowledge", () => ({
  listKnowledgeBases: mocks.listKnowledgeBases,
  listDocuments: vi.fn(), listVersions: vi.fn(), listChunks: vi.fn(),
  createDocument: vi.fn(), createKnowledgeBase: vi.fn(), createVersion: vi.fn(), deleteDocument: vi.fn(), ingestVersion: vi.fn(), retrieveKnowledge: vi.fn(),
}));

const StatePanelStub = {
  name: "StatePanel",
  props: ["state", "title", "description", "actionLabel"],
  emits: ["action"],
  template: `<div class="state-panel" :class="\`state-panel--${state}\`" role="status"><strong>{{ title }}</strong><span v-if="description">{{ description }}</span><button v-if="actionLabel" @click="$emit('action')">{{ actionLabel }}</button></div>`,
};

const mountView = () => mount(KnowledgeWorkbench, {
  global: {
    directives: { loading: () => undefined },
    components: { StatePanel: StatePanelStub, ElTable, ElTableColumn, ElTag },
    stubs: {
      PageHeader: true,
      PageToolbar: true,
      SurfaceCard: { template: "<div><slot/><slot name='header'/></div>" },
      "el-button": { template: "<button @click=\"$emit('click')\"><slot /></button>" },
      "el-dialog": true, "el-form": true, "el-form-item": true, "el-input": true,
      "el-input-number": true, "el-select": true, "el-option": true, "el-slider": true,
      "el-alert": true, "el-empty": true, "el-icon": true,
    },
  },
});

describe("Knowledge UI-04 states", () => {
  beforeEach(() => vi.resetAllMocks());

  it("shows loading while knowledge bases are requested", async () => {
    mocks.listKnowledgeBases.mockReturnValueOnce(new Promise(() => undefined));
    const wrapper = mountView();
    await nextTick();
    expect(wrapper.find(".state-panel").classes()).toContain("state-panel--loading");
  });

  it("shows success workspace when knowledge bases exist", async () => {
    mocks.listKnowledgeBases.mockResolvedValueOnce({ items: [{ id: "kb-1", name: "企业知识库", status: "active" }] });
    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.find(".state-panel").exists()).toBe(false);
    expect(wrapper.find(".grid").exists()).toBe(true);
  });

  it("provides retry action for recoverable loading failure", async () => {
    mocks.listKnowledgeBases.mockRejectedValueOnce(new Error("network"));
    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.find(".state-panel").classes()).toContain("state-panel--error");
    mocks.listKnowledgeBases.mockResolvedValueOnce({ items: [{ id: "kb-1", name: "企业知识库", status: "active" }] });
    await wrapper.find(".state-panel button").trigger("click");
    await flushPromises();
    expect(mocks.listKnowledgeBases).toHaveBeenCalledTimes(2);
    expect(wrapper.find(".state-panel").exists()).toBe(false);
  });

  it("exposes an action for the empty state", async () => {
    mocks.listKnowledgeBases.mockResolvedValueOnce({ items: [] });
    const wrapper = mountView();
    await flushPromises();
    const panel = wrapper.find(".state-panel");
    expect(panel.exists()).toBe(true);
    expect(panel.classes()).toContain("state-panel--empty");
    expect(panel.text()).toContain("创建知识库");
    expect(panel.find("button").exists()).toBe(true);
  });

  it.each([
    ["empty", { items: [] }, "暂无知识库"],
    ["permission", { response: { status: 403 } }, "无权访问知识库"],
    ["error", new Error("network"), "知识库加载失败"],
  ] as const)("maps %s response to shared state", async (state, response, title) => {
    if (state === "empty") mocks.listKnowledgeBases.mockResolvedValueOnce(response);
    else mocks.listKnowledgeBases.mockRejectedValueOnce(response);
    const wrapper = mountView();
    await flushPromises();
    const panel = wrapper.find(".state-panel");
    expect(panel.classes()).toContain(`state-panel--${state}`);
    expect(panel.text()).toContain(title);
  });

  it("keeps unknown knowledge status explicit in the workspace", async () => {
    mocks.listKnowledgeBases.mockResolvedValueOnce({ items: [{ id: "kb-1", name: "企业知识库", status: "future_status_v2" }] });
    const wrapper = mountView();
    await flushPromises();
    await nextTick();
    expect(wrapper.text()).toContain("未知状态（future_status_v2）");
  });
});
