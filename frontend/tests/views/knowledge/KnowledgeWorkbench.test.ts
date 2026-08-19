import { describe, expect, it, vi, beforeEach } from "vitest";
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
  stubs: {
    "el-table": true,
    "el-table-column": true,
    "el-card": true,
    "el-button": true,
    "el-input": true,
    "el-input-number": true,
    "el-alert": true,
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
    vi.mocked(api.listKnowledgeBases).mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20,
    });

    const wrapper = mount(KnowledgeWorkbench, { global });

    await vi.waitFor(() => {
      expect(api.listKnowledgeBases).toHaveBeenCalled();
    });

    expect(wrapper.text()).toContain("Knowledge 知识管理");
    expect(wrapper.text()).toContain("Retrieval Debug");
  });

  it("shows API failure state", async () => {
    vi.mocked(api.listKnowledgeBases).mockRejectedValue(new Error("network"));

    const wrapper = mount(KnowledgeWorkbench, { global });

    await vi.waitFor(() => {
      expect(wrapper.text()).toContain("network");
    });
  });
});
