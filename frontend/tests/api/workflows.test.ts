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
    del.mockResolvedValue({ data: undefined });

    await workflowApi.triggers("w1");
    await workflowApi.createTrigger("w1", { name: "Manual trigger", trigger_type: "manual", config: {} });
    await workflowApi.updateTrigger("w1", "t1", { status: "disabled" });
    await workflowApi.deleteTrigger("w1", "t1");

    expect(get).toHaveBeenCalledWith("/workflows/w1/triggers");
    expect(post).toHaveBeenCalledWith("/workflows/w1/triggers", { name: "Manual trigger", trigger_type: "manual", config: {} });
    expect(patch).toHaveBeenCalledWith("/workflows/w1/triggers/t1", { status: "disabled" });
    expect(del).toHaveBeenCalledWith("/workflows/w1/triggers/t1");
  });

  it("queries the persisted scheduler status through the formal workflow trigger contract", async () => {
    get.mockResolvedValue({ data: { id: "s1", trigger_id: "t1", lease_active: false } });
    const response = await workflowApi.schedule("w1", "t1");
    expect(get).toHaveBeenCalledWith("/workflows/w1/triggers/t1/schedule");
    expect(response.data.trigger_id).toBe("t1");
  });

  it("creates a webhook trigger with secret config without inventing a second endpoint", async () => {
    post.mockResolvedValue({ data: {} });
    await workflowApi.createTrigger("w1", {
      name: "Webhook trigger",
      trigger_type: "webhook",
      config: { auth_mode: "secret", secret: "1234567890123456", event_id_field: "event_id" },
    });
    expect(post).toHaveBeenCalledWith("/workflows/w1/triggers", {
      name: "Webhook trigger",
      trigger_type: "webhook",
      config: { auth_mode: "secret", secret: "1234567890123456", event_id_field: "event_id" },
    });
  });

  it("invokes a trigger with an optional idempotency key", async () => {
    post.mockResolvedValue({ data: {} });
    await workflowApi.invokeTrigger("w1", "t1", { order_id: "o1" }, "trigger-request-1");
    expect(post).toHaveBeenCalledWith(
      "/workflows/w1/triggers/t1/invoke",
      { input_data: { order_id: "o1" } },
      { headers: { "Idempotency-Key": "trigger-request-1" } },
    );
  });

  it("creates and runs an execution", async () => {
    post.mockResolvedValue({ data: {} });
    await workflowApi.createExecution("w1", { order_id: "o1" });
    await workflowApi.runExecution("e1");
    expect(post).toHaveBeenNthCalledWith(1, "/workflows/w1/executions", { input_data: { order_id: "o1" } }, undefined);
    expect(post).toHaveBeenNthCalledWith(2, "/workflows/executions/e1/run");
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

  it("controls failed and active executions", async () => {
    post.mockResolvedValue({ data: {} });
    await workflowApi.cancelExecution("e1", "operator requested stop");
    await workflowApi.retryExecution("e2");
    expect(post).toHaveBeenNthCalledWith(1, "/workflows/executions/e1/cancel", { reason: "operator requested stop" });
    expect(post).toHaveBeenNthCalledWith(2, "/workflows/executions/e2/retry");
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
