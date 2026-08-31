import { describe, expect, it, vi, beforeEach } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import KnowledgeWorkbench from "@/views/knowledge/components/KnowledgeWorkbench.vue";
import StatePanel from "@/components/ui/StatePanel.vue";

const listKnowledgeBases = vi.fn();
vi.mock("@/api/knowledge", () => ({
  listKnowledgeBases,
  listDocuments: vi.fn(), listVersions: vi.fn(), listChunks: vi.fn(),
  createDocument: vi.fn(), createKnowledgeBase: vi.fn(), createVersion: vi.fn(), deleteDocument: vi.fn(), ingestVersion: vi.fn(), retrieveKnowledge: vi.fn(),
}));
vi.mock("element-plus", () => ({ ElMessage: { error: vi.fn(), success: vi.fn() }, ElMessageBox: { confirm: vi.fn() } }));

const mountView = () => mount(KnowledgeWorkbench, { global: { stubs: { PageHeader: true, PageToolbar: true, SurfaceCard: { template: "<div><slot/><slot name='header'/></div>" }, "el-button": true, "el-table": true, "el-table-column": true, "el-dialog": true, "el-form": true, "el-form-item": true, "el-input": true, "el-input-number": true, "el-select": true, "el-option": true, "el-slider": true, "el-alert": true, "el-empty": true } } });

describe("Knowledge UI-04 states", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows loading while knowledge bases are requested", () => {
    listKnowledgeBases.mockReturnValueOnce(new Promise(() => undefined));
    const wrapper = mountView();
    expect(wrapper.findComponent(StatePanel).props("state")).toBe("loading");
  });

  it("shows success workspace when knowledge bases exist", async () => {
    listKnowledgeBases.mockResolvedValueOnce({ items: [{ id: "kb-1", name: "企业知识库", status: "active" }] });
    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.findComponent(StatePanel).exists()).toBe(false);
    expect(wrapper.text()).toContain("知识资产工作台");
  });

  it.each([
    ["empty", { items: [] }, "暂无知识库"],
    ["permission", { response: { status: 403 } }, "无权访问知识库"],
    ["error", new Error("network"), "知识库加载失败"],
  ] as const)("maps %s response to shared state", async (state, response, title) => {
    if (state === "empty") listKnowledgeBases.mockResolvedValueOnce(response);
    else listKnowledgeBases.mockRejectedValueOnce(response);
    const wrapper = mountView();
    await flushPromises();
    const panel = wrapper.findComponent(StatePanel);
    expect(panel.props("state")).toBe(state);
    expect(panel.text()).toContain(title);
  });
});
