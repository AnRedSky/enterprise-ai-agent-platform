import { beforeEach, describe, expect, it, vi } from "vitest";

const { get, post, patch, del } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn() }));
vi.mock("../../src/api/request", () => ({ request: { get, post, patch, delete: del } }));

import { workflowApi } from "../../src/api/workflows";

describe("workflowApi", () => {
  beforeEach(() => {
    get.mockReset();
    post.mockReset();
    patch.mockReset();
    del.mockReset();
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

  it("manages workflow triggers", async () => {
    get.mockResolvedValue({ data: [] });
    post.mockResolvedValue({ data: {} });
    patch.mockResolvedValue({ data: {} });

    await workflowApi.triggers("w1");
    await workflowApi.createTrigger("w1", { name: "Manual trigger", trigger_type: "manual", config: {} });
    await workflowApi.updateTrigger("w1", "t1", { status: "disabled" });
    await workflowApi.deleteTrigger("w1", "t1");

    expect(get).toHaveBeenCalledWith("/workflows/w1/triggers");
    expect(post).toHaveBeenCalledWith("/workflows/w1/triggers", { name: "Manual trigger", trigger_type: "manual", config: {} });
    expect(patch).toHaveBeenCalledWith("/workflows/w1/triggers/t1", { status: "disabled" });
    expect(post).toHaveBeenLastCalledWith("/runtime/operator-actions/workflow-triggers/t1/delete", { confirm: true });
  });

  it("exposes canonical trigger lifecycle governance actions", async () => {
    post.mockResolvedValue({ data: {} });
    await workflowApi.enableTrigger("w1", "t1");
    await workflowApi.disableTrigger("w1", "t1");
    expect(post).toHaveBeenNthCalledWith(1, "/runtime/operator-actions/workflow-triggers/t1/enable", { confirm: true });
    expect(post).toHaveBeenNthCalledWith(2, "/runtime/operator-actions/workflow-triggers/t1/disable", { confirm: true });
  });

  it("queries the persisted scheduler status through the formal workflow trigger contract", async () => {
    get.mockResolvedValue({ data: { id: "s1", trigger_id: "t1", lease_active: false } });
    const response = await workflowApi.schedule("w1", "t1");
    expect(get).toHaveBeenCalledWith("/workflows/w1/triggers/t1/schedule");
    expect(response.data.trigger_id).toBe("t1");
  });

  it("invokes a trigger through Operator Action governance with an idempotency key", async () => {
    post.mockResolvedValue({ data: { resource_type: "workflow_execution", action: "invoke", result: { id: "e1" } } });
    await workflowApi.invokeTrigger("w1", "t1", { order_id: "o1" }, "trigger-request-1");
    expect(post).toHaveBeenCalledWith(
      "/runtime/operator-actions/workflow-triggers/t1/invoke",
      { input_data: { order_id: "o1" } },
      { headers: { "Idempotency-Key": "trigger-request-1" } },
    );
  });

  it("creates and lists executions without changing the creation contract", async () => {
    get.mockResolvedValue({ data: [] });
    post.mockResolvedValue({ data: {} });
    await workflowApi.createExecution("w1", { order_id: "o1" });
    await workflowApi.listExecutions("w1");
    expect(post).toHaveBeenCalledWith("/workflows/w1/executions", { input_data: { order_id: "o1" } }, undefined);
    expect(get).toHaveBeenCalledWith("/workflows/w1/executions");
  });

  it("sends an idempotency key when creating an execution", async () => {
    post.mockResolvedValue({ data: {} });
    await workflowApi.createExecution("w1", { order_id: "o1" }, "request-1");
    expect(post).toHaveBeenCalledWith(
      "/workflows/w1/executions",
      { input_data: { order_id: "o1" } },
      { headers: { "Idempotency-Key": "request-1" } },
    );
  });

  it("routes Execution lifecycle actions through Operator Action governance", async () => {
    const result = { id: "e1", status: "running" };
    post.mockResolvedValue({ data: { resource_type: "workflow_execution", action: "run", result } });
    await workflowApi.runExecution("e1");
    await workflowApi.cancelExecution("e1", "operator requested stop");
    await workflowApi.retryExecution("e2", "retry-request-1");
    await workflowApi.resumeExecution("e3");

    expect(post).toHaveBeenNthCalledWith(1, "/runtime/operator-actions/workflow-executions/e1/run", { confirm: false }, undefined);
    expect(post).toHaveBeenNthCalledWith(2, "/runtime/operator-actions/workflow-executions/e1/cancel", { confirm: true, reason: "operator requested stop" }, undefined);
    expect(post).toHaveBeenNthCalledWith(3, "/runtime/operator-actions/workflow-executions/e2/retry", { confirm: true }, { headers: { "Idempotency-Key": "retry-request-1" } });
    expect(post).toHaveBeenNthCalledWith(4, "/runtime/operator-actions/workflow-executions/e3/resume", { confirm: true }, undefined);
  });

  it("generates an idempotency key for retry when the caller does not supply one", async () => {
    post.mockResolvedValue({ data: { resource_type: "workflow_execution", action: "retry", result: { id: "e2" } } });
    await workflowApi.retryExecution("e2");
    expect(post).toHaveBeenCalledWith(
      "/runtime/operator-actions/workflow-executions/e2/retry",
      { confirm: true },
      { headers: { "Idempotency-Key": expect.stringMatching(/^retry-/) } },
    );
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
