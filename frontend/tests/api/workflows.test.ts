import { beforeEach, describe, expect, it, vi } from "vitest";

const { get, post, patch } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn() }));
vi.mock("../../src/api/request", () => ({ request: { get, post, patch } }));

import { workflowApi } from "../../src/api/workflows";

describe("workflowApi", () => {
  beforeEach(() => {
    get.mockReset();
    post.mockReset();
    patch.mockReset();
  });

  it("lists and creates workflows", async () => {
    get.mockResolvedValue({ data: [] });
    post.mockResolvedValue({ data: {} });
    await workflowApi.list();
    await workflowApi.create({ name: "demo", description: "test" });
    expect(get).toHaveBeenCalledWith("/workflows");
    expect(post).toHaveBeenCalledWith("/workflows", { name: "demo", description: "test" });
  });

  it("manages versions and publish governance", async () => {
    get.mockResolvedValue({ data: [] });
    post.mockResolvedValue({ data: {} });
    await workflowApi.versions("w1");
    await workflowApi.createVersion("w1", { nodes: [], edges: [] });
    await workflowApi.publish("w1", "v1");
    expect(get).toHaveBeenCalledWith("/workflows/w1/versions");
    expect(post).toHaveBeenNthCalledWith(1, "/workflows/w1/versions", { definition: { nodes: [], edges: [] } });
    expect(post).toHaveBeenNthCalledWith(2, "/workflows/w1/versions/v1/publish");
  });

  it("creates and runs an execution", async () => {
    post.mockResolvedValue({ data: {} });
    await workflowApi.createExecution("w1", { order_id: "o1" });
    await workflowApi.runExecution("e1");
    expect(post).toHaveBeenNthCalledWith(1, "/workflows/w1/executions", { input_data: { order_id: "o1" } });
    expect(post).toHaveBeenNthCalledWith(2, "/workflows/executions/e1/run");
  });

  it("queries execution status, nodes, trace and audit", async () => {
    get.mockResolvedValue({ data: { items: [] } });
    await workflowApi.execution("e1");
    await workflowApi.executionNodes("e1");
    await workflowApi.trace("e1");
    await workflowApi.audit({ page: 1, page_size: 50, workflow_id: "w1" });
    expect(get).toHaveBeenNthCalledWith(1, "/workflows/executions/e1");
    expect(get).toHaveBeenNthCalledWith(2, "/workflows/executions/e1/nodes");
    expect(get).toHaveBeenNthCalledWith(3, "/runtime/executions/e1/trace");
    expect(get).toHaveBeenNthCalledWith(4, "/runtime/audit-logs", { params: { page: 1, page_size: 50, workflow_id: "w1" } });
  });

  it("updates workflow metadata", async () => {
    patch.mockResolvedValue({ data: {} });
    await workflowApi.update("w1", { name: "updated" });
    expect(patch).toHaveBeenCalledWith("/workflows/w1", { name: "updated" });
  });
});
