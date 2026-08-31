import { describe, expect, it, vi, beforeEach } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { ElTable, ElTableColumn, ElTag } from "element-plus";
import DashboardOverview from "@/views/dashboard/components/DashboardOverview.vue";

const mocks = vi.hoisted(() => ({
  listAgents: vi.fn(),
  listTools: vi.fn(),
  executions: vi.fn(),
}));
vi.mock("@/api/agents", () => ({ listAgents: mocks.listAgents }));
vi.mock("@/api/tools", () => ({ listTools: mocks.listTools }));
vi.mock("@/api/runtime", () => ({ runtimeApi: { executions: mocks.executions } }));

const StatePanelStub = {
  name: "StatePanel",
  props: ["state", "title", "description", "actionLabel"],
  emits: ["action"],
  template: `<div class="state-panel" :class="\`state-panel--\${state}\`" role="status"><strong>{{ title }}</strong><span v-if="description">{{ description }}</span><button v-if="actionLabel" @click="$emit('action')">{{ actionLabel }}</button></div>`,
};

function mountView() {
  return mount(DashboardOverview, {
    global: {
      directives: { loading: () => undefined },
      components: { StatePanel: StatePanelStub, ElTable, ElTableColumn, ElTag },
      stubs: {
        PageHeader: true,
        MetricCard: true,
        SurfaceCard: true,
        "el-button": { template: "<button @click=\"$emit('click')\"><slot /></button>" },
        "el-empty": true,
        "el-alert": true,
        "el-icon": true,
      },
    },
  });
}
function ok(items: unknown[] = [], total = items.length) { return { data: { total, items } }; }

async function resolveDashboardSuccess() {
  mocks.listAgents.mockResolvedValueOnce([{ status: "published" }]);
  mocks.listTools.mockResolvedValueOnce([{ enabled: true }]);
  mocks.executions.mockResolvedValueOnce(ok([{ execution_id: "e1", status: "completed" }]));
  mocks.executions.mockResolvedValueOnce(ok([], 0));
}

describe("Dashboard UI-04 states", () => {
  beforeEach(() => vi.resetAllMocks());

  it("renders loading while aggregate APIs are pending", async () => {
    mocks.listAgents.mockReturnValue(new Promise(() => {}));
    mocks.listTools.mockReturnValue(new Promise(() => {}));
    mocks.executions.mockReturnValue(new Promise(() => {}));
    const wrapper = mountView();
    await nextTick();
    expect(wrapper.find(".state-panel").classes()).toContain("state-panel--loading");
  });

  it("renders empty when all aggregate datasets are empty", async () => {
    mocks.listAgents.mockResolvedValue([]);
    mocks.listTools.mockResolvedValue([]);
    mocks.executions.mockResolvedValue(ok());
    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.find(".state-panel").classes()).toContain("state-panel--empty");
  });

  it("renders permission for an aggregate 403", async () => {
    const denied = { response: { status: 403 } };
    mocks.listAgents.mockRejectedValue(denied);
    mocks.listTools.mockRejectedValue(denied);
    mocks.executions.mockRejectedValue(denied);
    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.find(".state-panel").classes()).toContain("state-panel--permission");
  });

  it("renders error for recoverable aggregate failure and retries", async () => {
    mocks.listAgents.mockRejectedValueOnce(new Error("network"));
    mocks.listTools.mockResolvedValueOnce([]);
    mocks.executions.mockResolvedValueOnce(ok());
    mocks.executions.mockResolvedValueOnce(ok([], 0));
    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.find(".state-panel").classes()).toContain("state-panel--error");

    await resolveDashboardSuccess();
    await wrapper.find(".state-panel button").trigger("click");
    await flushPromises();

    expect(wrapper.find(".metrics").exists()).toBe(true);
    expect(mocks.listAgents).toHaveBeenCalledTimes(2);
    expect(mocks.executions).toHaveBeenCalledTimes(4);
  });

  it("renders dashboard content after successful aggregate load", async () => {
    await resolveDashboardSuccess();
    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.find(".metrics").exists()).toBe(true);
  });

  it("preserves unknown execution statuses instead of coercing them", async () => {
    mocks.listAgents.mockResolvedValueOnce([{ status: "published" }]);
    mocks.listTools.mockResolvedValueOnce([{ enabled: true }]);
    mocks.executions.mockResolvedValueOnce(ok([{ execution_id: "e1", status: "provider_pending_v2" }]));
    mocks.executions.mockResolvedValueOnce(ok([], 0));
    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.text()).toContain("未知状态（provider_pending_v2）");
  });
});
