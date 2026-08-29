import { describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import Integrations from "@/views/integrations/index.vue";
import { integrationApi } from "@/api/integrations";

vi.mock("@/api/integrations", () => ({
  integrationApi: { destinations: vi.fn(), subscriptions: vi.fn(), createDestination: vi.fn(), createSubscription: vi.fn() },
}));

describe("Integrations", () => {
  it("展示出站目标和事件订阅", async () => {
    vi.mocked(integrationApi.destinations).mockResolvedValue({ data: [{ id: "d1", tenant_id: "t1", name: "生产告警", endpoint_url: "https://example.com/hook", secret_ref: "secret/webhook", headers: {}, enabled: true, created_at: "2026-08-29T08:00:00Z", updated_at: "2026-08-29T08:00:00Z" }] } as never);
    vi.mocked(integrationApi.subscriptions).mockResolvedValue({ data: [{ id: "s1", tenant_id: "t1", destination_id: "d1", event_type: "runtime.execution.completed", priority: 100, enabled: true, filter_config: {}, created_at: "2026-08-29T08:00:00Z", updated_at: "2026-08-29T08:00:00Z" }] } as never);
    const wrapper = mount(Integrations);
    await vi.waitFor(() => expect(wrapper.text()).toContain("生产告警"));
    expect(wrapper.text()).toContain("runtime.execution.completed");
    expect(wrapper.text()).toContain("1 个已启用");
  });

  it("没有 Destination 时禁用 Subscription 创建入口", async () => {
    vi.mocked(integrationApi.destinations).mockResolvedValue({ data: [] } as never);
    vi.mocked(integrationApi.subscriptions).mockResolvedValue({ data: [] } as never);
    const wrapper = mount(Integrations);
    await vi.waitFor(() => expect(wrapper.text()).toContain("暂无 Destination"));
    const button = wrapper.findAll("button").find((item) => item.text().includes("新建 Subscription"));
    expect(button).toBeDefined();
    expect((button!.element as HTMLButtonElement).disabled).toBe(true);
  });
});
