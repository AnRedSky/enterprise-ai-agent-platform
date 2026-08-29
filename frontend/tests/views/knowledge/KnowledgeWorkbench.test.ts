import { beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import KnowledgeWorkbench from "@/views/knowledge/components/KnowledgeWorkbenchZh.vue";
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

  it("展示知识库与知识检索区域，并统一使用中文", async () => {
    vi.mocked(api.listKnowledgeBases).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 });
    const wrapper = mount(KnowledgeWorkbench, { global });
    await vi.waitFor(() => expect(api.listKnowledgeBases).toHaveBeenCalled());
    expect(wrapper.text()).toContain("知识库管理");
    expect(wrapper.text()).toContain("知识检索调试");
    expect(wrapper.text()).toContain("关键词检索 v2");
    expect(wrapper.text()).not.toContain("Retrieval Debug");
  });

  it("展示接口失败状态", async () => {
    vi.mocked(api.listKnowledgeBases).mockRejectedValue(new Error("network"));
    const wrapper = mount(KnowledgeWorkbench, { global });
    await vi.waitFor(() => expect(wrapper.text()).toContain("network"));
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

  it("混合检索发送权重并保留评分明细", async () => {
    vi.mocked(api.listKnowledgeBases).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 });
    vi.mocked(api.retrieveKnowledge).mockResolvedValue({
      query: "审批", top_k: 5, min_score: 0, retrieval_mode: "hybrid",
      results: [{ document_id: "doc-1", document_version_id: "ver-1", chunk_id: "chunk-1", chunk_index: 1,
        source_document: "审批制度", source_uri: null, relevance_score: 0.82, citation: "审批制度#1",
        content: "审批流程需要部门负责人确认。", matched_terms: ["审批"], retrieval_mode: "hybrid",
        retrieval_sources: ["lexical", "vector"], hybrid_score_breakdown: { lexical_score: 0.9, vector_score: 0.75,
          lexical_weight: 0.4, vector_weight: 0.6, fused_score: 0.81, support: ["lexical", "vector"] } }],
    });
    const wrapper = mount(KnowledgeWorkbench, { global });
    await vi.waitFor(() => expect(api.listKnowledgeBases).toHaveBeenCalled());
    wrapper.vm.query = "审批"; wrapper.vm.retrievalMode = "hybrid"; wrapper.vm.lexicalWeight = 0.4; wrapper.vm.vectorWeight = 0.6;
    await wrapper.vm.search();
    expect(api.retrieveKnowledge).toHaveBeenCalledWith({ query: "审批", top_k: 5, knowledge_base_id: undefined,
      mode: "hybrid", lexical_weight: 0.4, vector_weight: 0.6 });
    expect(wrapper.vm.results[0].hybrid_score_breakdown?.fused_score).toBe(0.81);
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
