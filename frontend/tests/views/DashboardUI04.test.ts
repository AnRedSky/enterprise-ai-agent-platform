import { describe, expect, it, vi, beforeEach } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { nextTick } from "vue";
import DashboardOverview from "@/views/dashboard/components/DashboardOverview.vue";
import StatePanel from "@/components/ui/StatePanel.vue";

const mocks = vi.hoisted(() => ({
  listAgents: vi.fn(),
  listTools: vi.fn(),
  executions: vi.fn(),
}));
vi.mock("@/api/agents", () => ({ listAgents: mocks.listAgents }));
vi.mock("@/api/tools", () => ({ listTools: mocks.listTools }));
vi.mock("@/api/runtime", () => ({ runtimeApi: { executions: mocks.executions } }));

function mountView() {
  return mount(DashboardOverview, {
    global: {
      directives: { loading: () => undefined },
      stubs: {
        PageHeader: true,
        MetricCard: true,
        SurfaceCard: true,
        "el-button": true,
        "el-table": true,
        "el-table-column": true,
        "el-tag": true,
        "el-empty": true,
        "el-alert": true,
      },
    },
  });
}
function ok(items: unknown[] = []) { return { data: { total: items.length, items } }; }

describe("Dashboard UI-04 states", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders loading while aggregate APIs are pending", async () => {
    mocks.listAgents.mockReturnValue(new Promise(() => {}));
    mocks.listTools.mockReturnValue(new Promise(() => {}));
    mocks.executions.mockReturnValue(new Promise(() => {}));
    const wrapper = mountView();
    await nextTick();
    expect(wrapper.findComponent(StatePanel).props("state")).toBe("loading");
  });

  it("renders empty when all aggregate datasets are empty", async () => {
    mocks.listAgents.mockResolvedValue([]); mocks.listTools.mockResolvedValue([]); mocks.executions.mockResolvedValue(ok());
    const wrapper = mountView(); await flushPromises();
    expect(wrapper.findComponent(StatePanel).props("state")).toBe("empty");
  });

  it("renders permission for an aggregate 403", async () => {
    const denied = { response: { status: 403 } }; mocks.listAgents.mockRejectedValue(denied); mocks.listTools.mockRejectedValue(denied); mocks.executions.mockRejectedValue(denied);
    const wrapper = mountView(); await flushPromises();
    expect(wrapper.findComponent(StatePanel).props("state")).toBe("permission");
  });

  it("renders error for recoverable aggregate failure", async () => {
    mocks.listAgents.mockRejectedValue(new Error("network")); mocks.listTools.mockResolvedValue([]); mocks.executions.mockResolvedValue(ok());
    const wrapper = mountView(); await flushPromises();
    expect(wrapper.findComponent(StatePanel).props("state")).toBe("error");
  });

  it("renders dashboard content after successful aggregate load", async () => {
    mocks.listAgents.mockResolvedValue([{ status: "published" }]); mocks.listTools.mockResolvedValue([{ enabled: true }]); mocks.executions.mockResolvedValue(ok([{ execution_id: "e1", status: "completed" }]));
    const wrapper = mountView(); await flushPromises();
    expect(wrapper.find(".metrics").exists()).toBe(true);
  });
});
