import { beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";

const { globalApi, workerApi, schedulerApi } = vi.hoisted(() => ({
  globalApi: vi.fn(),
  workerApi: vi.fn(),
  schedulerApi: vi.fn(),
}));
vi.mock("../../src/api/runtimeOperations", () => ({ runtimeOperationsApi: { global: globalApi } }));
vi.mock("../../src/api/runtimeDiagnostics", () => ({ runtimeDiagnosticsApi: { worker: workerApi, scheduler: schedulerApi } }));
vi.mock("element-plus", () => ({ ElMessage: { error: vi.fn() } }));

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

const posture = {
  window_hours: 24, since: "2026-08-31T00:00:00", generated_at: "2026-08-31T12:00:00Z",
  filters: { workflow_id: null, agent_id: null, trigger_id: null, execution_id: null, execution_status: null },
  executions: { total: 3, status_counts: { pending: 1, running: 1, completed: 1 }, active_count: 2, recovery_count: 0, items: [] },
  workflows: { total: 1, status_counts: { published: 1 } },
  triggers: { total: 2, status_counts: { enabled: 2 }, scheduled_enabled: 1 },
  worker: { liveness: "unknown", liveness_reason_code: "NO_DURABLE_HEARTBEAT_FACT", running_frontiers: 1, pending_frontiers: 2, leased_frontiers: 1, expired_leases: 0, active_worker_owners: 1 },
  scheduler: { liveness: "unknown", liveness_reason_code: "NO_DURABLE_HEARTBEAT_FACT", enabled_scheduled_triggers: 1, durable_frontier_backlog: 2 },
};
const workerDiagnostics = {
  window_hours: 24, generated_at: "2026-08-31T12:00:00Z", liveness: "unknown", liveness_reason_code: "NO_DURABLE_HEARTBEAT_FACT",
  frontier: { total: 4, status_counts: { running: 1, pending: 2, failed: 1 }, running: 1, pending: 2, completed: 0, failed: 1 },
  leases: { without_expiry: 1, active: 2, expired: 1 },
  owners: [{ worker_owner: "worker-a", claim_count: 3 }],
  recent_errors: [{ id: "frontier-1", execution_id: "execution-1", status: "failed", attempt: 2, worker_owner: "worker-a", worker_lease_expires_at: null, error_code: "NODE_TIMEOUT", created_at: "2026-08-31T11:00:00Z" }],
};
const schedulerDiagnostics = {
  generated_at: "2026-08-31T12:00:00Z", liveness: "unknown", liveness_reason_code: "NO_DURABLE_HEARTBEAT_FACT",
  durable: { enabled_scheduled_triggers: 1, disabled_scheduled_triggers: 1, pending_frontier_items: 2 },
  triggers: [{ id: "trigger-1", workflow_id: "workflow-1", name: "每日同步", status: "enabled", config: {}, updated_at: "2026-08-31T11:00:00Z" }],
};

const global = { stubs, directives: { loading: () => undefined } };

describe("GlobalRuntimeOperations", () => {
  beforeEach(() => {
    globalApi.mockReset(); workerApi.mockReset(); schedulerApi.mockReset();
    globalApi.mockResolvedValue({ data: posture });
    workerApi.mockResolvedValue({ data: workerDiagnostics });
    schedulerApi.mockResolvedValue({ data: schedulerDiagnostics });
  });

  it("renders canonical runtime posture and diagnostics without deriving liveness", async () => {
    const wrapper = mount(GlobalRuntimeOperations, { global });
    await vi.waitFor(() => expect(globalApi).toHaveBeenCalled());
    await vi.waitFor(() => expect(workerApi).toHaveBeenCalled());
    await vi.waitFor(() => expect(schedulerApi).toHaveBeenCalled());
    expect(globalApi).toHaveBeenCalledWith({ window_hours: 24, limit: 50 });
    expect(workerApi).toHaveBeenCalledWith(24, 50);
    expect(schedulerApi).toHaveBeenCalledWith(50);
    expect((wrapper.vm as any).workerDiagnostics.recent_errors[0].error_code).toBe("NODE_TIMEOUT");
    expect((wrapper.vm as any).schedulerDiagnostics.triggers[0].name).toBe("每日同步");
    expect(wrapper.text()).toContain("全局 Runtime Operations");
    expect(wrapper.text()).toContain("NO_DURABLE_HEARTBEAT_FACT");
    expect(wrapper.text()).toContain("Worker Claim / Lease");
    expect(wrapper.text()).toContain("3");
  });

  it("keeps the global posture visible when diagnostics requests fail", async () => {
    workerApi.mockRejectedValue(new Error("worker diagnostics unavailable"));
    schedulerApi.mockRejectedValue(new Error("scheduler diagnostics unavailable"));
    const wrapper = mount(GlobalRuntimeOperations, { global });
    await vi.waitFor(() => expect(globalApi).toHaveBeenCalled());
    await vi.waitFor(() => expect((wrapper.vm as any).diagnosticsError).toBe(true));
    expect(wrapper.text()).toContain("全局 Runtime Operations");
    expect(wrapper.text()).toContain("诊断数据暂时不可用");
    expect(wrapper.text()).not.toContain("worker diagnostics unavailable");
  });

  it("shows a user-safe error when the global posture request fails", async () => {
    globalApi.mockRejectedValue(new Error("request failed"));
    const wrapper = mount(GlobalRuntimeOperations, { global });
    await vi.waitFor(() => expect(wrapper.text()).toContain("全局 Runtime 数据加载失败"));
  });
});
