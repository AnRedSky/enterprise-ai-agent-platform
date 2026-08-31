import { describe, expect, it, vi } from "vitest";
import { shallowMount } from "@vue/test-utils";
import KnowledgeWorkbench from "@/views/knowledge/components/KnowledgeWorkbench.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import StatePanel from "@/components/ui/StatePanel.vue";

vi.mock("@/api/knowledge", () => ({
  createDocument: vi.fn(), createKnowledgeBase: vi.fn(), createVersion: vi.fn(), deleteDocument: vi.fn(),
  ingestVersion: vi.fn().mockResolvedValue(undefined), listChunks: vi.fn().mockResolvedValue([]), listDocuments: vi.fn().mockResolvedValue({ items: [] }),
  listKnowledgeBases: vi.fn().mockResolvedValue({ items: [] }), listVersions: vi.fn().mockResolvedValue([]), retrieveKnowledge: vi.fn(),
}));
vi.mock("element-plus", () => ({ ElMessage: { error: vi.fn(), success: vi.fn() }, ElMessageBox: { confirm: vi.fn() } }));

const pageHeaderStub = { props: ["title", "eyebrow", "description"], template: "<header><h1>{{ title }}</h1><slot name=\"actions\"/></header>" };
const statePanelStub = { props: ["state", "title", "description", "actionLabel"], template: "<div class=\"state-panel\"><strong>{{ title }}</strong><span>{{ description }}</span><button v-if=\"actionLabel\">{{ actionLabel }}</button></div>" };
const elementStubs = { "el-button": true, "el-alert": true, "el-table": true, "el-table-column": true, "el-empty": true, "el-dialog": true, "el-form": true, "el-form-item": true, "el-input": true, "el-select": true, "el-option": true, "el-input-number": true, "el-slider": true };

describe("KnowledgeWorkbench UI-03 migration", () => {
  it("uses the shared page header and first-class state pattern", () => {
    const wrapper = shallowMount(KnowledgeWorkbench, { global: { stubs: { ...elementStubs, PageHeader: pageHeaderStub, StatePanel: statePanelStub } } });
    expect(wrapper.findComponent(PageHeader).exists()).toBe(true);
    expect(wrapper.findComponent(StatePanel).exists()).toBe(true);
    expect(wrapper.findComponent(PageHeader).props("title")).toBe("知识库管理");
    expect(wrapper.findComponent(StatePanel).props("state")).toBe("loading");
    expect(wrapper.findComponent(StatePanel).props("title")).toBe("正在加载知识库");
  });

  it("keeps the empty knowledge-base state and recovery action explicit", async () => {
    const wrapper = shallowMount(KnowledgeWorkbench, { global: { stubs: { ...elementStubs, PageHeader: pageHeaderStub, StatePanel: statePanelStub } } });
    await vi.waitFor(() => expect((wrapper.vm as any).loading).toBe(false));
    const state = wrapper.findComponent(StatePanel);
    expect(state.props("state")).toBe("empty");
    expect(state.props("title")).toBe("暂无知识库");
    expect(state.props("description")).toBe("请先创建知识库，再继续管理文档和版本。");
    expect(state.props("actionLabel")).toBe("创建知识库");
  });
});
