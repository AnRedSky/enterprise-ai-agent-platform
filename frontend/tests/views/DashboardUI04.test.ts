import { describe, expect, it, vi, beforeEach } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import DashboardOverview from "@/views/dashboard/components/DashboardOverview.vue";
import StatePanel from "@/components/ui/StatePanel.vue";

const listAgents = vi.fn();
const listTools = vi.fn();
const executions = vi.fn();
vi.mock("@/api/agents", () => ({ listAgents }));
vi.mock("@/api/tools", () => ({ listTools }));
vi.mock("@/api/runtime", () => ({ runtimeApi: { executions } }));

function mountView() { return mount(DashboardOverview, { global: { stubs: { PageHeader: true, MetricCard: true, SurfaceCard: true, "el-button": true, "el-table": true, "el-table-column": true, "el-tag": true, "el-empty": true, "el-alert": true, StatePanel: false } } }); }
function ok(items: unknown[] = []) { return { data: { total: items.length, items } }; }

describe("Dashboard UI-04 states", () => {
  beforeEach(() => vi.clearAllMocks());
  it("renders loading while aggregate APIs are pending", () => {
    listAgents.mockReturnValue(new Promise(() => {})); listTools.mockReturnValue(new Promise(() => {})); executions.mockReturnValue(new Promise(() => {}));
    const wrapper = mountView();
    expect(wrapper.findComponent(StatePanel).props("state")).toBe("loading");
  });
  it("renders empty when all aggregate datasets are empty", async () => {
    listAgents.mockResolvedValue([]); listTools.mockResolvedValue([]); executions.mockResolvedValue(ok());
    const wrapper = mountView(); await flushPromises();
    expect(wrapper.findComponent(StatePanel).props("state")).toBe("empty");
  });
  it("renders permission for an aggregate 403", async () => {
    const denied = { response: { status: 403 } }; listAgents.mockRejectedValue(denied); listTools.mockRejectedValue(denied); executions.mockRejectedValue(denied);
    const wrapper = mountView(); await flushPromises();
    expect(wrapper.findComponent(StatePanel).props("state")).toBe("permission");
  });
  it("renders error for recoverable aggregate failure", async () => {
    listAgents.mockRejectedValue(new Error("network")); listTools.mockResolvedValue([]); executions.mockResolvedValue(ok());
    const wrapper = mountView(); await flushPromises();
    expect(wrapper.findComponent(StatePanel).props("state")).toBe("error");
  });
  it("renders dashboard content after successful aggregate load", async () => {
    listAgents.mockResolvedValue([{ status: "published" }]); listTools.mockResolvedValue([{ enabled: true }]); executions.mockResolvedValue(ok([{ execution_id: "e1", status: "completed" }]));
    const wrapper = mountView(); await flushPromises();
    expect(wrapper.find(".metrics").exists()).toBe(true);
  });
});
