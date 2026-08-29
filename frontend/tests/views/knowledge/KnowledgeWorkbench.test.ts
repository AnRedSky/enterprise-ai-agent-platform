import { beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import KnowledgeWorkbench from "@/views/knowledge/components/KnowledgeWorkbench.vue";
import * as api from "@/api/knowledge";

vi.mock("@/api/knowledge", () => ({
  listKnowledgeBases: vi.fn(), listDocuments: vi.fn(), listVersions: vi.fn(), listChunks: vi.fn(),
  createKnowledgeBase: vi.fn(), createDocument: vi.fn(), createVersion: vi.fn(), deleteDocument: vi.fn(),
  ingestVersion: vi.fn(), retrieveKnowledge: vi.fn(), updateDocument: vi.fn(), updateKnowledgeBase: vi.fn(),
}));

const global = {
  directives: { loading: () => undefined },
  stubs: {
    "el-card": { template: "<section><slot name=\"header\"/><slot /></section>" },
    "el-alert": { props: ["title"], template: "<div class=\"alert\">{{ title }}</div>" },
    "el-table": { template: "<div><slot /></div>" },
    "el-table-column": { template: "<div><slot :row=\"{}\" /></div>" },
    "el-button": true, "el-input": true, "el-input-number": true, "el-select": true,
    "el-option": true, "el-slider": true, "el-empty": true, "el-dialog": true,
    "el-form": true, "el-form-item": true,
  },
};

describe("KnowledgeWorkbench", () => {
  beforeEach(() => vi.clearAllMocks());

  it("统一使用中文界面文本，同时保留必要技术标识", async () => {
    vi.mocked(api.listKnowledgeBases).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 });
    const wrapper = mount(KnowledgeWorkbench, { global });
    await vi.waitFor(() => expect(api.listKnowledgeBases).toHaveBeenCalled());
    expect(wrapper.text()).toContain("知识库管理");
    expect(wrapper.text()).toContain("知识检索调试");
    expect(wrapper.text()).not.toContain("Knowledge 知识管理");
    expect(wrapper.text()).not.toContain("Retrieval Debug");
  });

  it("接口失败时不直接展示后端异常文本", async () => {
    vi.mocked(api.listKnowledgeBases).mockRejectedValue(new Error("500 Internal Server Error"));
    const wrapper = mount(KnowledgeWorkbench, { global });
    await vi.waitFor(() => expect(wrapper.text()).toContain("知识库加载失败，请刷新后重试"));
    expect(wrapper.text()).not.toContain("500 Internal Server Error");
  });

  it("状态、来源类型和检索方式统一映射为中文并保留技术值", async () => {
    vi.mocked(api.listKnowledgeBases).mockResolvedValue({
      items: [{ id: "kb-1", name: "企业知识库", description: "", owner_id: "u1", status: "active", created_at: "", updated_at: "" }],
      total: 1, page: 1, page_size: 20,
    });
    const wrapper = mount(KnowledgeWorkbench, { global });
    await vi.waitFor(() => expect(api.listKnowledgeBases).toHaveBeenCalled());
    expect((wrapper.vm as any).statusLabel("active")).toBe("已启用（active）");
    expect((wrapper.vm as any).statusLabel("unknown_status")).toBe("未知状态（unknown_status）");
    expect((wrapper.vm as any).sourceTypeLabel("manual")).toBe("手动录入（manual）");
    expect((wrapper.vm as any).retrievalModeLabel("lexical-v2")).toBe("关键词检索 v2（lexical-v2）");
    expect((wrapper.vm as any).retrievalModeLabel("vector")).toBe("向量检索（vector）");
    expect((wrapper.vm as any).retrievalModeLabel("hybrid")).toBe("混合检索（hybrid）");
  });

  it("执行检索并保留引用详情", async () => {
    vi.mocked(api.listKnowledgeBases).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 });
    vi.mocked(api.retrieveKnowledge).mockResolvedValue({
      query: "报销规则", top_k: 5, min_score: 0, retrieval_mode: "lexical-v2",
      results: [{ document_id: "doc-1", document_version_id: "ver-1", chunk_id: "chunk-1", chunk_index: 0,
        source_document: "员工手册", source_uri: "https://example.test/employee-handbook", relevance_score: 0.93,
        citation: "员工手册#chunk-0", content: "差旅报销应在规定期限内提交。", matched_terms: ["报销"], retrieval_mode: "lexical-v2" }],
    });
    const wrapper = mount(KnowledgeWorkbench, { global });
    await vi.waitFor(() => expect(api.listKnowledgeBases).toHaveBeenCalled());
    wrapper.vm.query = "报销规则";
    await wrapper.vm.search();
    expect(api.retrieveKnowledge).toHaveBeenCalledWith({ query: "报销规则", top_k: 5, knowledge_base_id: undefined,
      mode: "lexical-v2", lexical_weight: undefined, vector_weight: undefined });
    expect(wrapper.vm.results[0].citation).toBe("员工手册#chunk-0");
  });

  it("检索问题为空时不调用接口并提示用户", async () => {
    vi.mocked(api.listKnowledgeBases).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 });
    const wrapper = mount(KnowledgeWorkbench, { global });
    await vi.waitFor(() => expect(api.listKnowledgeBases).toHaveBeenCalled());
    await wrapper.vm.search();
    expect(api.retrieveKnowledge).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("请输入检索问题");
  });
});
