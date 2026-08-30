import { describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";

const globalApi = vi.fn();
vi.mock("../../src/api/runtimeOperations", () => ({
  runtimeOperationsApi: { global: globalApi },
}));
vi.mock("element-plus", () => ({
  ElMessage: { error: vi.fn() },
}));

import GlobalRuntimeOperations from "../../src/views/integrations/GlobalRuntimeOperations.vue";

const stubs = {
  "el-card": { template: "<section><slot name=\"header\"/><slot/></section>" },
  "el-select": { template: "<select><slot/></select>" },
  "el-option": { template: "<option />" },
  "el-button": { template: "<button><slot/></button>" },
  "el-alert": { template: "<div><slot/>{{ title }}</div>", props: ["title"] },
  "el-table": { template: "<div><slot/></div>" },
  "el-table-column": { template: "<div />" },
  "el-tag": { template: "<span><slot/></span>" },
};

const global = { stubs, directives: { loading: () => undefined } };

describe("GlobalRuntimeOperations", () => {
  it("renders canonical runtime posture and unknown liveness", async () => {
    globalApi.mockResolvedValue({ data: {
      window_hours: 24, since: "2026-08-31T00:00:00", generated_at: "2026-08-31T12:00:00Z",
      filters: { workflow_id: null, agent_id: null, trigger_id: null, execution_id: null, execution_status: null },
      executions: { total: 3, status_counts: { pending: 1, running: 1, completed: 1 }, active_count: 2, recovery_count: 0, items: [] },
      workflows: { total: 1, status_counts: { published: 1 } },
      triggers: { total: 2, status_counts: { enabled: 2 }, scheduled_enabled: 1 },
      worker: { liveness: "unknown", liveness_reason_code: "NO_DURABLE_HEARTBEAT_FACT", running_frontiers: 1, pending_frontiers: 2, leased_frontiers: 1, expired_leases: 0, active_worker_owners: 1 },
      scheduler: { liveness: "unknown", liveness_reason_code: "NO_DURABLE_HEARTBEAT_FACT", enabled_scheduled_triggers: 1, durable_frontier_backlog: 2 },
    } });
    const wrapper = mount(GlobalRuntimeOperations, { global });
    await Promise.resolve();
    await wrapper.vm.$nextTick();
    expect(globalApi).toHaveBeenCalledWith({ window_hours: 24, limit: 50 });
    expect(wrapper.text()).toContain("全局 Runtime Operations");
    expect(wrapper.text()).toContain("NO_DURABLE_HEARTBEAT_FACT");
    expect(wrapper.text()).toContain("3");
  });

  it("shows an error when the global contract request fails", async () => {
    globalApi.mockRejectedValue(new Error("request failed"));
    const wrapper = mount(GlobalRuntimeOperations, { global });
    await Promise.resolve();
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain("全局 Runtime 数据加载失败");
  });
});
