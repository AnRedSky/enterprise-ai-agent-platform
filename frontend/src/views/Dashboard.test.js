import { describe, expect, it, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
const { listAgents, listTools, executions } = vi.hoisted(() => ({
    listAgents: vi.fn(),
    listTools: vi.fn(),
    executions: vi.fn(),
}));
vi.mock("../api/agents", () => ({ listAgents }));
vi.mock("../api/tools", () => ({ listTools }));
vi.mock("../api/runtime", () => ({ runtimeApi: { executions } }));
vi.mock("element-plus", () => ({ ElMessage: { error: vi.fn() } }));
import Dashboard from "./Dashboard.vue";
const stubs = {
    "el-button": { template: "<button><slot/></button>" },
    "el-alert": { template: "<div class=\"alert\"><slot/>{{ title }}</div>", props: ["title"] },
    "el-card": { template: "<div><slot name=\"header\"/><slot/></div>" },
};
const global = { stubs, directives: { loading: () => undefined } };
describe("Dashboard.vue", () => {
    beforeEach(() => {
        listAgents.mockReset();
        listTools.mockReset();
        executions.mockReset();
    });
    it("loads and renders lifecycle metrics", async () => {
        listAgents.mockResolvedValue([
            { id: "a1", name: "A", status: "published" },
            { id: "a2", name: "B", status: "draft" },
        ]);
        listTools.mockResolvedValue([{ id: "t1", enabled: true }, { id: "t2", enabled: false }]);
        executions.mockImplementation(({ status }) => Promise.resolve({ data: { total: status === "failed" ? 2 : 8 } }));
        const wrapper = mount(Dashboard, { global });
        await vi.waitFor(() => expect(executions).toHaveBeenCalledTimes(2));
        // executions() being called does not mean Promise.all() has completed;
        // wait for the rendered metrics before asserting the reactive state.
        await vi.waitFor(() => expect(wrapper.text()).toContain("8"));
        expect(wrapper.text()).toContain("2");
        expect(wrapper.text()).toContain("1");
        expect(wrapper.text()).toContain("1/2");
    });
    it("renders a clear error when dashboard data fails", async () => {
        listAgents.mockRejectedValue(new Error("network"));
        listTools.mockResolvedValue([]);
        executions.mockResolvedValue({ data: { total: 0 } });
        const wrapper = mount(Dashboard, { global });
        await vi.waitFor(() => expect(wrapper.text()).toContain("network"));
    });
});
