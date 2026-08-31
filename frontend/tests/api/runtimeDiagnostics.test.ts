import { beforeEach, describe, expect, it, vi } from "vitest";

const { get } = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("../../src/api/request", () => ({ request: { get } }));

import { runtimeDiagnosticsApi, type RuntimeSchedulerDiagnostics, type RuntimeWorkerDiagnostics } from "../../src/api/runtimeDiagnostics";

describe("runtimeDiagnosticsApi", () => {
  beforeEach(() => get.mockReset());

  it("requests worker diagnostics with bounded query parameters", async () => {
    get.mockResolvedValue({ data: {} as RuntimeWorkerDiagnostics });
    await runtimeDiagnosticsApi.worker(24, 50);
    expect(get).toHaveBeenCalledWith("/runtime/diagnostics/worker", { params: { window_hours: 24, limit: 50 } });
  });

  it("requests scheduler diagnostics with the owner detail limit", async () => {
    get.mockResolvedValue({ data: {} as RuntimeSchedulerDiagnostics });
    await runtimeDiagnosticsApi.scheduler(20);
    expect(get).toHaveBeenCalledWith("/runtime/diagnostics/scheduler", { params: { limit: 20 } });
  });

  it("uses backend liveness and reason fields without deriving process health", async () => {
    get.mockResolvedValue({ data: { liveness: "unknown", liveness_reason_code: "NO_DURABLE_HEARTBEAT_FACT" } });
    const response = await runtimeDiagnosticsApi.worker();
    expect(response.data.liveness).toBe("unknown");
    expect(response.data.liveness_reason_code).toBe("NO_DURABLE_HEARTBEAT_FACT");
  });
});
