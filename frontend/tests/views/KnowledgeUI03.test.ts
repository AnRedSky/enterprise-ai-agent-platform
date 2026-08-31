import { describe, expect, it, vi } from "vitest";
import { shallowMount } from "@vue/test-utils";
import KnowledgeWorkbench from "@/views/knowledge/components/KnowledgeWorkbench.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import PageToolbar from "@/components/ui/PageToolbar.vue";
import SurfaceCard from "@/components/ui/SurfaceCard.vue";

vi.mock("@/api/knowledge", () => ({
  createDocument: vi.fn(), createKnowledgeBase: vi.fn(), createVersion: vi.fn(), deleteDocument: vi.fn(),
  ingestVersion: vi.fn(), listChunks: vi.fn().mockResolvedValue([]), listDocuments: vi.fn().mockResolvedValue({ items: [] }),
  listKnowledgeBases: vi.fn().mockResolvedValue({ items: [] }), listVersions: vi.fn().mockResolvedValue([]),
  retrieveKnowledge: vi.fn(),
}));
vi.mock("element-plus", () => ({ ElMessage: { error: vi.fn(), success: vi.fn() }, ElMessageBox: { confirm: vi.fn() } }));

describe("KnowledgeWorkbench UI-03 migration", () => {
  it("uses shared page header, toolbar and surface patterns", () => {
    const wrapper = shallowMount(KnowledgeWorkbench, { global: { stubs: { "el-button": true, "el-alert": true, "el-table": true, "el-table-column": true, "el-empty": true, "el-dialog": true, "el-form": true, "el-form-item": true, "el-input": true, "el-select": true, "el-option": true, "el-input-number": true, "el-slider": true } } });
    expect(wrapper.findComponent(PageHeader).exists()).toBe(true);
    expect(wrapper.findComponent(PageToolbar).exists()).toBe(true);
    expect(wrapper.findAllComponents(SurfaceCard).length).toBeGreaterThanOrEqual(3);
    expect(wrapper.text()).toContain("知识库管理");
    expect(wrapper.text()).toContain("知识检索调试");
  });

  it("keeps knowledge base and retrieval empty states explicit", async () => {
    const wrapper = shallowMount(KnowledgeWorkbench, { global: { stubs: { "el-button": true, "el-alert": true, "el-table": true, "el-table-column": true, "el-empty": { template: "<div>{{ description }}</div>", props: ["description"] }, "el-dialog": true, "el-form": true, "el-form-item": true, "el-input": true, "el-select": true, "el-option": true, "el-input-number": true, "el-slider": true } } });
    await vi.waitFor(() => expect((wrapper.vm as any).loading).toBe(false));
    expect(wrapper.text()).toContain("暂无知识库，请先创建知识库。");
    expect(wrapper.text()).toContain("输入问题后执行知识检索调试");
  });
});
