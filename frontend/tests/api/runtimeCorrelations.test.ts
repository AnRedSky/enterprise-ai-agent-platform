import { beforeEach, describe, expect, it, vi } from "vitest";

const { get } = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("../../src/api/request", () => ({ request: { get } }));

import { runtimeCorrelationsApi, type RuntimeCorrelationResponse } from "../../src/api/runtimeCorrelations";

describe("runtimeCorrelationsApi", () => {
  beforeEach(() => get.mockReset());

  it("requests execution correlation with independent trace and audit pagination", async () => {
    get.mockResolvedValue({ data: {} as RuntimeCorrelationResponse });
    await runtimeCorrelationsApi.execution("execution-a", {
      trace_page: 2,
      trace_page_size: 20,
      audit_page: 3,
      audit_page_size: 10,
      trace_event_type: "execution.state_changed",
      audit_status: "success",
    });
    expect(get).toHaveBeenCalledWith("/runtime/correlations/executions/execution-a", {
      params: {
        trace_page: 2,
        trace_page_size: 20,
        audit_page: 3,
        audit_page_size: 10,
        trace_event_type: "execution.state_changed",
        audit_status: "success",
      },
    });
  });

  it("keeps reverse correlation endpoints distinct", async () => {
    get.mockResolvedValue({ data: {} as RuntimeCorrelationResponse });
    await runtimeCorrelationsApi.trace("trace-a");
    await runtimeCorrelationsApi.audit("audit-a");
    await runtimeCorrelationsApi.operatorAction("action-a");
    expect(get.mock.calls.map(([url]) => url)).toEqual([
      "/runtime/correlations/traces/trace-a",
      "/runtime/correlations/audits/audit-a",
      "/runtime/correlations/operator-actions/action-a",
    ]);
  });

  it("does not add a client-side tenant identifier", async () => {
    get.mockResolvedValue({ data: {} as RuntimeCorrelationResponse });
    await runtimeCorrelationsApi.execution("execution-a");
    expect(get).toHaveBeenCalledWith("/runtime/correlations/executions/execution-a", { params: {} });
    expect(JSON.stringify(get.mock.calls[0])).not.toContain("tenant_id");
  });
});
