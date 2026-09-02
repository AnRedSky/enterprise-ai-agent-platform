import { describe, expect, it, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import RuntimeCorrelations from "@/views/runtime/components/RuntimeCorrelations.vue";
import { runtimeCorrelationsApi } from "@/api/runtimeCorrelations";

const route = { query: {} as Record<string, string> };
vi.mock("vue-router", () => ({ useRoute: () => route }));
vi.mock("@/api/runtimeCorrelations", () => ({ runtimeCorrelationsApi: { execution: vi.fn(), trace: vi.fn(), audit: vi.fn(), operatorAction: vi.fn() } }));
const result = { execution: { id: "e1", workflow_id: "w1", workflow_version_id: "v2", status: "completed", error_code: null, created_at: "2026-09-02T00:00:00Z" }, traces: { items: [], page: 1, page_size: 20, total: 0 }, audits: { items: [], page: 1, page_size: 20, total: 0 }, operator_actions: [] };
const global = { stubs: {
  "el-form": { template: "<form><slot/></form>" }, "el-select": { props: ["modelValue"], emits: ["update:modelValue"], template: "<div><slot/></div>" }, "el-option": { template: "<option/>" }, "el-input": { props: ["modelValue", "placeholder"], emits: ["update:modelValue"], template: "<input :value=""modelValue"" />" }, "el-button": { props: ["loading"], emits: ["click"], template: "<button @click="$emit('click')"><slot/></button>" }, "el-alert": { props: ["title"], template: "<div>{{ title }}</div>" }, "el-empty": { props: ["description"], template: "<div>{{ description }}</div>" }, "el-card": { template: "<div><slot name='header'/><slot/></div>" }, "el-tag": { template: "<span><slot/></span>" }, "el-descriptions": { template: "<div><slot/></div>" }, "el-descriptions-item": { template: "<div><slot/></div>" }, "el-table": { template: "<div><slot/></div>" }, "el-table-column": { template: "<span/>" }, "el-pagination": { template: "<div/>" },
} };
beforeEach(() => { vi.clearAllMocks(); route.query = {}; vi.mocked(runtimeCorrelationsApi.execution).mockResolvedValue({ data: result } as never); });

describe("RuntimeCorrelations", () => {
  it("uses execution_id deep-link context as the default correlation focus", () => { route.query = { execution_id: "e1", workflow_id: "w1", source: "workflow-lifecycle", tab: "correlations", focus_type: "execution", focus_id: "e1" }; const wrapper = mount(RuntimeCorrelations, { global }); expect((wrapper.vm as any).focusType).toBe("execution"); expect((wrapper.vm as any).focusId).toBe("e1"); });
  it("queries the backend with the deep-linked Execution ID without deriving Trace/Audit IDs", async () => { route.query = { execution_id: "e1", focus_type: "execution", focus_id: "e1" }; const wrapper = mount(RuntimeCorrelations, { global }); await (wrapper.vm as any).query(); expect(runtimeCorrelationsApi.execution).toHaveBeenCalledWith("e1", { trace_page: 1, trace_page_size: 20, audit_page: 1, audit_page_size: 20 }); expect(wrapper.text()).toContain("Execution"); });
});
