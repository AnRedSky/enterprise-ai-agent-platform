import { describe, expect, it, vi } from "vitest";
import { workflowApi } from "@/api/workflows";
import { request } from "@/api/request";

vi.mock("@/api/request", () => ({ request: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() } }));

describe("workflow trigger operator actions", () => {
  it.each([["enableTrigger", "enable"], ["disableTrigger", "disable"], ["deleteTrigger", "delete"]] as const)("uses canonical %s endpoint and confirm=true", async (method, action) => {
    vi.mocked(request.post).mockResolvedValueOnce({ data: { resource_type: "workflow_trigger", action, result: { id: "t1", status: action === "enable" ? "enabled" : "disabled" } } } as never);
    const response = await workflowApi[method]("w1", "t1");
    expect(request.post).toHaveBeenCalledWith(`/runtime/operator-actions/workflow-triggers/t1/${action}`, { confirm: true });
    expect(response.data).toEqual({ id: "t1", status: action === "enable" ? "enabled" : "disabled" });
  });

  it("keeps invoke idempotency-key behavior on canonical operator endpoint", async () => {
    vi.mocked(request.post).mockResolvedValueOnce({ data: { resource_type: "workflow_execution", action: "invoke", result: { id: "e1" } } } as never);
    const response = await workflowApi.invokeTrigger("w1", "t1", {}, "invoke-test-key");
    expect(request.post).toHaveBeenCalledWith("/runtime/operator-actions/workflow-triggers/t1/invoke", { input_data: {} }, { headers: { "Idempotency-Key": "invoke-test-key" } });
    expect(response.data).toEqual({ id: "e1" });
  });
});
