import { describe, expect, it, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
const { executions, executionEvents } = vi.hoisted(() => ({
    executions: vi.fn(),
    executionEvents: vi.fn(),
}));
vi.mock("../api/runtime", () => ({ runtimeApi: { executions, executionEvents } }));
vi.mock("element-plus", () => ({ ElMessage: { error: vi.fn() } }));
import Runtime from "./Runtime.vue";
const stubs = {
    "el-card": { template: "<div><slot name=\"header\"/><slot/></div>" },
    "el-form": { template: "<form><slot/></form>" },
    "el-input": { template: "<input />" },
    "el-button": { template: "<button><slot/></button>" },
    "el-alert": { template: "<div class=\"alert\">Runtime 查询失败，请稍后重试</div>" },
    "el-empty": { template: "<div class=\"empty\">empty</div>" },
    "el-table": { template: "<div class=\"table\"><slot/></div>" },
    "el-table-column": { template: "<div/>" },
    "el-pagination": { template: "<div/>" },
    "el-drawer": { template: "<div><slot/></div>" },
    "el-descriptions": { template: "<div><slot/></div>" },
    "el-descriptions-item": { template: "<div><slot/></div>" },
    "el-timeline": { template: "<div><slot/></div>" },
    "el-timeline-item": { template: "<div><slot/></div>" },
};
const global = { stubs, directives: { loading: () => undefined } };
describe("Runtime.vue", () => {
    beforeEach(() => { executions.mockReset(); executionEvents.mockReset(); });
    it("renders empty state when execution list is empty", async () => {
        executions.mockResolvedValue({ data: { items: [], page: 1, page_size: 20, total: 0 } });
        const wrapper = mount(Runtime, { global });
        await vi.waitFor(() => expect(executions).toHaveBeenCalled());
        expect(wrapper.text()).toContain("empty");
    });
    it("renders error state when execution query fails", async () => {
        executions.mockRejectedValue(new Error("network"));
        const wrapper = mount(Runtime, { global });
        await vi.waitFor(() => expect(wrapper.text()).toContain("Runtime 查询失败，请稍后重试"));
    });
    it("loads execution events after opening a row", async () => {
        const item = { execution_id: "e1", request_id: "r1", trace_id: "t1", agent_id: "a1", status: "success", started_at: "2026-01-01" };
        executions.mockResolvedValue({ data: { items: [item], page: 1, page_size: 20, total: 1 } });
        executionEvents.mockResolvedValue({ data: { execution: item, items: [] } });
        const wrapper = mount(Runtime, { global });
        await vi.waitFor(() => expect(executions).toHaveBeenCalled());
        await wrapper.vm.open(item);
        expect(executionEvents).toHaveBeenCalledWith("e1");
    });
});
