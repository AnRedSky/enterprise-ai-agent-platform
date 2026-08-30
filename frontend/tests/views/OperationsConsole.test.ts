import { describe, expect, it, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { ElAlert, ElButton, ElCard, ElDivider, ElForm, ElInput, ElInputNumber, ElOption, ElPagination, ElProgress, ElSelect, ElSwitch, ElTabPane, ElTable, ElTableColumn, ElTabs, ElTag } from "element-plus";
import OperationsConsole from "@/views/integrations/OperationsConsole.vue";
import { runtimeOperationsApi } from "@/api/runtimeOperations";

vi.mock("@/api/runtimeOperations", () => ({
  runtimeOperationsApi: {
    overview: vi.fn(), alerts: vi.fn(), providers: vi.fn(), alertRules: vi.fn(), audit: vi.fn(), deadLetters: vi.fn(),
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
  vi.mocked(runtimeOperationsApi.overview).mockResolvedValue({ data: { window_hours: 24, since: "2026-08-29T00:00:00Z", generated_at: "2026-08-30T00:00:00Z", events: { total: 12, status_counts: { delivered: 10, failed: 2 } }, deliveries: { total: 12, status_counts: { delivered: 10, failed: 2 }, retry_count: 2, dead_letter_count: 1 }, slo: { target_percent: 99, delivery_success_percent: 99.5, error_budget_percent: 0.5, p95_delivery_latency_ms: 120 } } } as never);
  vi.mocked(runtimeOperationsApi.alerts).mockResolvedValue({ data: { items: [{ id: "a1", name: "delivery failure", status: "firing", severity: "warning", fired_at: "2026-08-30T08:00:00Z", recovered_at: null }] } } as never);
  vi.mocked(runtimeOperationsApi.alertRules).mockResolvedValue({ data: { items: [{ id: "r1", name: "Delivery SLO", metric_name: "runtime.notification.delivery", operator: "<", threshold: 99, window_minutes: 15, severity: "warning", enabled: true }] } } as never);
  vi.mocked(runtimeOperationsApi.providers).mockResolvedValue({ data: { items: [{ id: "p1", name: "primary-webhook", provider_type: "webhook", enabled: true, status: "healthy", last_checked_at: "2026-08-30T08:00:00Z" }] } } as never);
  vi.mocked(runtimeOperationsApi.audit).mockResolvedValue({ data: { items: [{ id: "audit1", action: "provider.health.probe", status: "success", actor_id: "u1", created_at: "2026-08-30T08:00:00Z" }] } } as never);
  vi.mocked(runtimeOperationsApi.deadLetters).mockResolvedValue({ data: { items: [], page: 1, page_size: 20, total: 0 } } as never);
  vi.mocked(runtimeOperationsApi.metricSeries).mockResolvedValue({ data: { items: [], metric_name: "runtime.notification.delivery", window_minutes: 60 } } as never);
});

describe("Runtime Operations Console", () => {
  it("renders backend 2.10-I operational facts", async () => {
    const wrapper = mountConsole();
    await vi.waitFor(() => expect(wrapper.text()).toContain("Runtime 企业运维中心"));
    expect(wrapper.text()).toContain("投递成功率");
    expect(wrapper.text()).toContain("99.50%");
    expect(runtimeOperationsApi.providers).toHaveBeenCalled();
    expect(runtimeOperationsApi.alertRules).toHaveBeenCalled();
  });

  it("exposes alert, provider, metrics, audit and dead-letter operational tabs", async () => {
    const wrapper = mountConsole();
    await vi.waitFor(() => expect(wrapper.text()).toContain("Provider"));
    expect(wrapper.text()).toContain("告警");
    expect(wrapper.text()).toContain("Metrics");
    expect(wrapper.text()).toContain("Audit");
    expect(wrapper.text()).toContain("死信");
  });
});
