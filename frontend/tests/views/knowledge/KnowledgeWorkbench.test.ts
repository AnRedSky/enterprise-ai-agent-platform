import { beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import KnowledgeWorkbench from "@/views/knowledge/components/KnowledgeWorkbench.vue";
import * as api from "@/api/knowledge";

vi.mock("@/api/knowledge", () => ({
  listKnowledgeBases: vi.fn(),
  listDocuments: vi.fn(),
  listVersions: vi.fn(),
  listChunks: vi.fn(),
  createKnowledgeBase: vi.fn(),
  createDocument: vi.fn(),
  createVersion: vi.fn(),
  deleteDocument: vi.fn(),
  ingestVersion: vi.fn(),
  retrieveKnowledge: vi.fn(),
  updateDocument: vi.fn(),
  updateKnowledgeBase: vi.fn(),
}));

const global = {
  directives: {
    loading: () => undefined,
  },
  stubs: {
    "el-card": { template: "<section><slot name=\"header\"/><slot /></section>" },
    "el-alert": { props: ["title"], template: "<div class=\"alert\">{{ title }}</div>" },
    "el-table": { template: "<div><slot /></div>" },
    "el-table-column": { template: "<div><slot :row=\"{}\" /></div>" },
    "el-button": true,
    "el-input": true,
    "el-input-number": true,
    "el-empty": true,
    "el-dialog": true,
    "el-form": true,
    "el-form-item": true,
  },
};

describe("KnowledgeWorkbench", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders knowledge and retrieval sections", async () => {
    vi.mocked(api.listKnowledgeBases).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 });
    const wrapper = mount(KnowledgeWorkbench, { global });
    await vi.waitFor(() => expect(api.listKnowledgeBases).toHaveBeenCalled());
    expect(wrapper.text()).toContain("Knowledge 知识管理");
    expect(wrapper.text()).toContain("Retrieval Debug");
  });

  it("shows API failure state", async () => {
    vi.mocked(api.listKnowledgeBases).mockRejectedValue(new Error("network"));
    const wrapper = mount(KnowledgeWorkbench, { global });
    await vi.waitFor(() => expect(wrapper.text()).toContain("network"));
  });

  it("executes retrieval and stores citation detail", async () => {
    vi.mocked(api.listKnowledgeBases).mockResolvedValue({
      items: [{ id: "kb-1", name: "企业知识库", description: "", owner_id: "owner-1", status: "active", created_at: "", updated_at: "" }],
      total: 1,
      page: 1,
      page_size: 20,
    });
    vi.mocked(api.retrieveKnowledge).mockResolvedValue({
      query: "报销规则",
      top_k: 5,
      results: [{
        document_id: "doc-1",
        document_version_id: "ver-1",
        chunk_id: "chunk-1",
        chunk_index: 0,
        source_document: "员工手册",
        source_uri: "https://example.test/employee-handbook",
        relevance_score: 0.93,
        citation: "员工手册#chunk-0",
        content: "差旅报销应在规定期限内提交。",
      }],
    });
    const wrapper = mount(KnowledgeWorkbench, { global });
    await vi.waitFor(() => expect(api.listKnowledgeBases).toHaveBeenCalled());
    wrapper.vm.query = "报销规则";
    await wrapper.vm.search();
    expect(api.retrieveKnowledge).toHaveBeenCalledWith({ query: "报销规则", top_k: 5, knowledge_base_id: undefined });
    expect(wrapper.vm.results[0].citation).toBe("员工手册#chunk-0");
  });

  it("shows retrieval input validation without calling the API", async () => {
    vi.mocked(api.listKnowledgeBases).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 });
    const wrapper = mount(KnowledgeWorkbench, { global });
    await vi.waitFor(() => expect(api.listKnowledgeBases).toHaveBeenCalled());
    await wrapper.vm.search();
    expect(api.retrieveKnowledge).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("请输入检索问题");
  });
});
