import { describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import ElementPlus from "element-plus";
import DeliveryConsole from "@/views/integrations/DeliveryConsole.vue";
import { integrationApi } from "@/api/integrations";

vi.mock("@/api/integrations", () => ({
  integrationApi: {
    deliveries: vi.fn(),
    deliveryAudit: vi.fn(),
    replayDelivery: vi.fn(),
  },
}));

const delivery = {
  id: "delivery-1",
  tenant_id: "tenant-1",
  subscription_id: "subscription-1",
  destination_id: "destination-1",
  integration_event_id: "event-1",
  status: "failed",
  attempt_count: 3,
  next_attempt_at: null,
  last_attempt_at: "2026-08-29T09:00:00Z",
  delivered_at: null,
  response_status_code: 503,
  last_error_code: "HTTP_ERROR",
  last_error_message: "upstream unavailable",
  created_at: "2026-08-29T08:00:00Z",
  updated_at: "2026-08-29T09:00:00Z",
};

describe("DeliveryConsole", () => {
  it("展示失败 Delivery，并提供 Audit 与 Replay 入口", async () => {
    vi.mocked(integrationApi.deliveries).mockResolvedValue({ data: [delivery] } as never);
    vi.mocked(integrationApi.deliveryAudit).mockResolvedValue({ data: [] } as never);
    const wrapper = mount(DeliveryConsole, { global: { plugins: [ElementPlus] } });

    await vi.waitFor(() => expect(wrapper.text()).toContain("失败"));
    expect(wrapper.text()).toContain("HTTP_ERROR");
    expect(wrapper.text()).toContain("Replay");
    expect(wrapper.text()).toContain("Audit");
  });

  it("打开 Audit 时按 Delivery ID 请求审计轨迹", async () => {
    vi.mocked(integrationApi.deliveries).mockResolvedValue({ data: [delivery] } as never);
    vi.mocked(integrationApi.deliveryAudit).mockResolvedValue({
      data: [{ id: "audit-1", delivery_id: "delivery-1", integration_event_id: "event-1", action: "delivery.failed", attempt_count: 3, status: "failed", response_status_code: 503, error_code: "HTTP_ERROR", error_message: "upstream unavailable", actor: "worker", created_at: "2026-08-29T09:00:00Z" }],
    } as never);
    const wrapper = mount(DeliveryConsole, { global: { plugins: [ElementPlus] } });

    await vi.waitFor(() => expect(wrapper.text()).toContain("delivery-1"));
    await wrapper.findAll("button").find((item) => item.text().includes("Audit"))!.trigger("click");
    await vi.waitFor(() => expect(integrationApi.deliveryAudit).toHaveBeenCalledWith("delivery-1"));
    expect(wrapper.text()).toContain("delivery.failed");
  });
});
