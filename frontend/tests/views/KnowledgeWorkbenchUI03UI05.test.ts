import { beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";

const api = vi.hoisted(() => ({
  listKnowledgeBases: vi.fn(), listDocuments: vi.fn(), listVersions: vi.fn(), listChunks: vi.fn(), retrieveKnowledge: vi.fn(),
  createKnowledgeBase: vi.fn(), createDocument: vi.fn(), createVersion: vi.fn(), ingestVersion: vi.fn(), deleteDocument: vi.fn(),
}));
vi.mock("@/api/knowledge", () => ({ ...api }));
vi.mock("element-plus", () => ({ ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() }, ElMessageBox: { confirm: vi.fn() } }));

import KnowledgeWorkbench from "@/views/knowledge/components/KnowledgeWorkbench.vue";

const base = { id: "kb-1", name: "企业知识库", description: "", owner_id: "u1", status: "active", created_at: "2026-01-01", updated_at: "2026-01-01" };
const document = { id: "doc-1", knowledge_base_id: "kb-1", title: "报销制度", source_type: "manual", source_uri: null, status: "active", current_version_id: "ver-1", created_at: "2026-01-01", updated_at: "2026-01-01" };
const version = { id: "ver-1", document_id: "doc-1", version: "v1", status: "ready", ingestion_status: "completed", source_uri: null, content_hash: "h1", content_text: "content", created_by: "u1", created_at: "2026-01-01" };

const global = { stubs: {
  PageHeader: { template: "<header><slot name=\"actions\" /></header>" },
  PageToolbar: { template: "<div class=\"toolbar\"><slot /></div>" },
  SurfaceCard: { props: ["title"], template: "<section class=\"surface-card\"><slot name=\"header\" /><slot /></section>" },
  StatePanel: { props: ["state", "title", "description"], template: "<div class=\"state-panel\">{{ state }} {{ title }} {{ description }}</div>" },
  "el-button": { props: ["loading", "disabled"], template: "<button :disabled=\"disabled\"><slot /></button>" },
  "el-table": { props: ["data"], template: "<div><slot /></div>" }, "el-table-column": { template: "<div />" },
  "el-input": { template: "<input />" }, "el-input-number": { template: "<input />" }, "el-select": { template: "<select><slot /></select>" }, "el-option": { template: "<option><slot /></option>" }, "el-slider": { template: "<input />" },
  "el-dialog": { props: ["modelValue"], template: "<div v-if=\"modelValue\"><slot /><slot name=\"footer\" /></div>" }, "el-form": { template: "<form><slot /></form>" }, "el-form-item": { template: "<div><slot /></div>" },
  "el-alert": { template: "<div><slot /></div>" }, "el-empty": { props: ["description"], template: "<div class=\"empty\">{{ description }}</div>" },
} };

describe("KnowledgeWorkbench UI-03/UI-05", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.listKnowledgeBases.mockResolvedValue({ items: [base], total: 1, page: 1, page_size: 20 });
    api.listDocuments.mockResolvedValue({ items: [document], total: 1, page: 1, page_size: 20 });
    api.listVersions.mockResolvedValue([version]);
    api.listChunks.mockResolvedValue([]);
  });

  it("renders the shared page header, toolbar and surface cards", async () => {
    const wrapper = mount(KnowledgeWorkbench, { global });
    await flushPromises();
    expect(wrapper.find("header").exists()).toBe(true);
    expect(wrapper.find(".toolbar").exists()).toBe(true);
    expect(wrapper.findAll(".surface-card").length).toBeGreaterThanOrEqual(3);
  });

  it("uses the shared permission state for a knowledge-base 403", async () => {
    api.listKnowledgeBases.mockRejectedValueOnce({ response: { status: 403 } });
    const wrapper = mount(KnowledgeWorkbench, { global });
    await flushPromises();
    expect(wrapper.find(".state-panel").text()).toContain("permission");
    expect(wrapper.text()).toContain("无权访问知识库");
  });

  it("preserves durable knowledge-base/document/version identifiers", async () => {
    const wrapper = mount(KnowledgeWorkbench, { global });
    await flushPromises();
    await (wrapper.vm as any).selectBase(base);
    expect(api.listDocuments).toHaveBeenCalledWith("kb-1");
    await (wrapper.vm as any).openDocument(document);
    expect(api.listVersions).toHaveBeenCalledWith("kb-1", "doc-1");
    await (wrapper.vm as any).openChunks(version);
    expect(api.listChunks).toHaveBeenCalledWith("ver-1");
  });

  it("uses explicit retrieval contract and preserves backend result facts", async () => {
    api.retrieveKnowledge.mockResolvedValueOnce({ query: "报销", top_k: 5, min_score: 0, retrieval_mode: "hybrid", results: [{ document_id: "doc-1", document_version_id: "ver-1", chunk_id: "chunk-1", chunk_index: 2, source_document: "报销制度", source_uri: null, relevance_score: 0.9, citation: "报销制度#2", content: "内容", matched_terms: ["报销"], retrieval_mode: "hybrid", retrieval_sources: ["lexical", "vector"] }] });
    const wrapper = mount(KnowledgeWorkbench, { global });
    await flushPromises();
    (wrapper.vm as any).query = "报销";
    (wrapper.vm as any).retrievalMode = "hybrid";
    await (wrapper.vm as any).search();
    expect(api.retrieveKnowledge).toHaveBeenCalledWith(expect.objectContaining({ query: "报销", top_k: 5, mode: "hybrid", knowledge_base_id: undefined }));
    expect((wrapper.vm as any).results[0].chunk_id).toBe("chunk-1");
  });
});
