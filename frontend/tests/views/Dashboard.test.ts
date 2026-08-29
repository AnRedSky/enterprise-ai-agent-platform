import { describe, expect, it, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";

const { listAgents, listTools, executions } = vi.hoisted(() => ({
  listAgents: vi.fn(),
  listTools: vi.fn(),
  executions: vi.fn(),
}));
vi.mock("../../src/api/agents", () => ({ listAgents }));
vi.mock("../../src/api/tools", () => ({ listTools }));
vi.mock("../../src/api/runtime", () => ({ runtimeApi: { executions } }));
vi.mock("element-plus", () => ({ ElMessage: { error: vi.fn() } }));

import Dashboard from "../../src/views/dashboard/components/DashboardOverview.vue";

const stubs = {
  "el-button": { template: "<button @click=\"$emit('click')\"><slot/></button>", emits: ["click"] },
  "el-alert": { template: "<div class=\"alert\"><slot/><span>{{ title }}</span><span>{{ description }}</span></div>", props: ["title", "description"] },
  "el-card": { template: "<div><slot name=\"header\"/><slot/></div>" },
  "el-tag": { template: "<span><slot/></span>" },
  "el-table": { template: "<div class=\"table\">{{ JSON.stringify(data) }}</div>", props: ["data"] },
  "el-table-column": { template: "<div />" },
  "el-empty": { template: "<div>{{ description }}</div>", props: ["description"] },
};
const global = { stubs, directives: { loading: () => undefined } };

describe("DashboardOverview", () => {
  beforeEach(() => {
    listAgents.mockReset();
    listTools.mockReset();
    executions.mockReset();
  });

  it("loads lifecycle metrics and recent runtime executions", async () => {
    listAgents.mockResolvedValue([
      { id: "a1", name: "A", status: "published" },
      { id: "a2", name: "B", status: "draft" },
    ]);
    listTools.mockResolvedValue([{ id: "t1", enabled: true }, { id: "t2", enabled: false }]);
    executions.mockImplementation(({ status, page_size }: { status?: string; page_size?: number }) =>
      Promise.resolve({ data: {
        total: status === "failed" ? 2 : 8,
        page: 1,
        page_size,
        items: status === "failed" ? [] : [{ execution_id: "execution-001", status: "completed", started_at: "2026-08-29T08:00:00Z", agent_id: "a1", duration_ms: 240 }],
      } }),
    );
    const wrapper = mount(Dashboard, { global });
    await vi.waitFor(() => expect(executions).toHaveBeenCalledTimes(2));
    await vi.waitFor(() => expect(wrapper.text()).toContain("8"));
    expect(wrapper.text()).toContain("2");
    expect(wrapper.text()).toContain("1");
    expect(wrapper.text()).toContain("1/2");
    expect(wrapper.text()).toContain("最近执行");
    expect(wrapper.text()).toContain("execution-001");
    expect(wrapper.text()).toContain("Agent 管理");
  });

  it("renders a clear error when dashboard data fails", async () => {
    listAgents.mockRejectedValue(new Error("network"));
    listTools.mockResolvedValue([]);
    executions.mockResolvedValue({ data: { total: 0, items: [] } });
    const wrapper = mount(Dashboard, { global });
    await vi.waitFor(() => expect(wrapper.text()).toContain("network"));
  });
});
