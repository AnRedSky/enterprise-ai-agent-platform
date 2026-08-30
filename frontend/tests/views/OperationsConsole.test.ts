import { describe, expect, it, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { ElAlert, ElButton, ElCard, ElDivider, ElForm, ElInput, ElInputNumber, ElOption, ElPagination, ElProgress, ElSelect, ElSwitch, ElTabPane, ElTable, ElTableColumn, ElTabs, ElTag } from "element-plus";
import OperationsConsole from "@/views/integrations/OperationsConsole.vue";
import { runtimeOperationsApi } from "@/api/runtimeOperations";

vi.mock("@/api/runtimeOperations", () => ({
  runtimeOperationsApi: {
    global: vi.fn(), overview: vi.fn(), alerts: vi.fn(), providers: vi.fn(), alertRules: vi.fn(), audit: vi.fn(), deadLetters: vi.fn(),
    metricSeries: vi.fn(), evaluateAlertRules: vi.fn(), setProviderEnabled: vi.fn(), probeProviderHealth: vi.fn(),
    setAlertRuleEnabled: vi.fn(), createMetricsSnapshot: vi.fn(), replayDeadLetters: vi.fn(), dimensions: vi.fn(),
  },
}));

const components = { ElAlert, ElButton, ElCard, ElDivider, ElForm, ElInput, ElInputNumber, ElOption, ElPagination, ElProgress, ElSelect, ElSwitch, ElTabPane, ElTable, ElTableColumn, ElTabs, ElTag };

function mountConsole() {
  return mount(OperationsConsole, { global: { components, directives: { loading: () => undefined } } });
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(runtimeOperationsApi.global).mockResolvedValue({ data: {
    window_hours: 24, since: "2026-08-29T00:00:00Z", generated_at: "2026-08-30T00:00:00Z",
    filters: { workflow_id: null, agent_id: null, trigger_id: null, execution_id: null, execution_status: null },
    executions: { total: 8, status_counts: { pending: 1, running: 2, completed: 4, failed: 1 }, active_count: 3, recovery_count: 1, items: [{ id: "ex1", workflow_id: "wf1", workflow_name: "订单处理", status: "running", current_node_id: "node-2", worker_owner: "worker-1", worker_attempt: 1, worker_lease_expires_at: "2026-08-30T00:05:00Z", error_code: null, started_at: "2026-08-29T23:00:00Z", ended_at: null, created_at: "2026-08-29T23:00:00Z" }] },
    workflows: { total: 3, status_counts: { active: 2, draft: 1 } },
    triggers: { total: 4, status_counts: { enabled: 3, disabled: 1 }, scheduled_enabled: 3 },
    worker: { liveness: "unknown", liveness_reason_code: "NO_DURABLE_HEARTBEAT_FACT", running_frontiers: 2, pending_frontiers: 1, leased_frontiers: 2, expired_leases: 1, active_worker_owners: 1 },
    scheduler: { liveness: "unknown", liveness_reason_code: "NO_DURABLE_HEARTBEAT_FACT", enabled_scheduled_triggers: 3, durable_frontier_backlog: 1 },
  } } as never);
  vi.mocked(runtimeOperationsApi.overview).mockResolvedValue({ data: { window_hours: 24, since: "2026-08-29T00:00:00Z", generated_at: "2026-08-30T00:00:00Z", events: { total: 12, status_counts: { delivered: 10, failed: 2 } }, deliveries: { total: 12, status_counts: { delivered: 10, failed: 2 }, retry_count: 2, dead_letter_count: 1 }, slo: { target_percent: 99, delivery_success_percent: 99.5, error_budget_percent: 0.5, p95_delivery_latency_ms: 120 } } } as never);
  vi.mocked(runtimeOperationsApi.alerts).mockResolvedValue({ data: { items: [{ id: "a1", name: "delivery failure", status: "firing", severity: "warning", fired_at: "2026-08-30T08:00:00Z", recovered_at: null }] } } as never);
  vi.mocked(runtimeOperationsApi.alertRules).mockResolvedValue({ data: { items: [{ id: "r1", name: "Delivery SLO", metric_name: "runtime.notification.delivery", operator: "<", threshold: 99, window_minutes: 15, severity: "warning", enabled: true }] } } as never);
  vi.mocked(runtimeOperationsApi.providers).mockResolvedValue({ data: { items: [{ id: "p1", name: "primary-webhook", provider_type: "webhook", enabled: true, status: "healthy", last_checked_at: "2026-08-30T08:00:00Z" }] } } as never);
  vi.mocked(runtimeOperationsApi.audit).mockResolvedValue({ data: { items: [{ id: "audit1", action: "provider.health.probe", status: "success", actor_id: "u1", created_at: "2026-08-30T08:00:00Z" }] } } as never);
  vi.mocked(runtimeOperationsApi.deadLetters).mockResolvedValue({ data: { items: [], page: 1, page_size: 20, total: 0 } } as never);
  vi.mocked(runtimeOperationsApi.metricSeries).mockResolvedValue({ data: { items: [], metric_name: "runtime.notification.delivery", window_minutes: 60 } } as never);
});

describe("Runtime Operations Console", () => {
  it("renders backend global runtime posture", async () => {
    const wrapper = mountConsole();
    await vi.waitFor(() => expect(wrapper.text()).toContain("全局运行态势"));
    expect(wrapper.text()).toContain("执行总量");
    expect(wrapper.text()).toContain("8");
    expect(wrapper.text()).toContain("未知（无持久化心跳）");
    expect(wrapper.text()).toContain("订单处理");
    expect(runtimeOperationsApi.global).toHaveBeenCalledWith({ window_hours: 24, limit: 50 });
  });

  it("renders backend 2.10-I operational facts", async () => {
    const wrapper = mountConsole();
    await vi.waitFor(() => expect(wrapper.text()).toContain("99.50%"));
    expect(wrapper.text()).toContain("Runtime 企业运维中心");
    expect(wrapper.text()).toContain("投递成功率");
    expect(runtimeOperationsApi.providers).toHaveBeenCalled();
    expect(runtimeOperationsApi.alertRules).toHaveBeenCalled();
  });

  it("exposes global and existing operational tabs", async () => {
    const wrapper = mountConsole();
    await vi.waitFor(() => expect(wrapper.text()).toContain("Provider"));
    expect(wrapper.text()).toContain("全局运行态势");
    expect(wrapper.text()).toContain("告警");
    expect(wrapper.text()).toContain("Metrics");
    expect(wrapper.text()).toContain("Audit");
    expect(wrapper.text()).toContain("死信");
  });
});
