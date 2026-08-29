import { describe, expect, it, vi } from "vitest";
import { integrationApi } from "@/api/integrations";
import { request } from "@/api/request";

vi.mock("@/api/request", () => ({ request: { get: vi.fn(), post: vi.fn() } }));

describe("integrationApi", () => {
  it("使用后端 Webhook Destination / Subscription Contract", async () => {
    vi.mocked(request.get).mockResolvedValue({ data: [] });
    vi.mocked(request.post).mockResolvedValue({ data: {} });

    await integrationApi.destinations();
    await integrationApi.subscriptions();
    await integrationApi.createDestination({ name: "prod", endpoint_url: "https://example.com/hook" });
    await integrationApi.createSubscription({ destination_id: "d1", event_type: "runtime.execution.completed" });

    expect(request.get).toHaveBeenNthCalledWith(1, "/webhooks/destinations");
    expect(request.get).toHaveBeenNthCalledWith(2, "/webhooks/subscriptions");
    expect(request.post).toHaveBeenNthCalledWith(1, "/webhooks/destinations", { name: "prod", endpoint_url: "https://example.com/hook" });
    expect(request.post).toHaveBeenNthCalledWith(2, "/webhooks/subscriptions", { destination_id: "d1", event_type: "runtime.execution.completed" });
  });
});
