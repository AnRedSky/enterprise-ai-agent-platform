import { beforeEach, describe, expect, it, vi } from "vitest";

const { get } = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock("./request", () => ({
  request: { get },
}));

import { runtimeApi } from "./runtime";

describe("runtimeApi", () => {
  beforeEach(() => get.mockReset());

  it("requests executions with pagination and filters", async () => {
    get.mockResolvedValue({ data: { items: [], page: 1, page_size: 20, total: 0 } });
    await runtimeApi.executions({ page: 1, page_size: 20, status: "failed" });
    expect(get).toHaveBeenCalledWith("/runtime/executions", { params: { page: 1, page_size: 20, status: "failed" } });
  });

  it("requests execution timeline by id", async () => {
    get.mockResolvedValue({ data: { execution: {}, items: [] } });
    await runtimeApi.executionEvents("execution-1");
    expect(get).toHaveBeenCalledWith("/runtime/executions/execution-1/events");
  });

  it("requests audit logs with filters", async () => {
    get.mockResolvedValue({ data: { items: [], page: 1, page_size: 20, total: 0 } });
    await runtimeApi.auditLogs({ page: 1, page_size: 20, agent_id: "agent-1" });
    expect(get).toHaveBeenCalledWith("/runtime/audit-logs", { params: { page: 1, page_size: 20, agent_id: "agent-1" } });
  });
});
