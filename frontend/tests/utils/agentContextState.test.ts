import { describe, expect, it } from "vitest";
import { isAgentPermissionError, loadAgentContext } from "@/utils/agentContextState";

describe("agentContextState", () => {
  it.each([
    [{ response: { status: 403 } }],
    [{ response: { data: { status: 403 } } }],
    [{ response: { data: { code: "FORBIDDEN" } } }],
    [{ status: "403" }],
  ])("recognizes permission errors from structured API shapes", (error) => {
    expect(isAgentPermissionError(error)).toBe(true);
  });

  it("does not classify ordinary backend failures as permission errors", () => {
    expect(isAgentPermissionError({ response: { status: 500 } })).toBe(false);
  });

  it("preserves permission as the terminal state for a rejected context load", async () => {
    const result = await loadAgentContext(() => Promise.reject({ response: { status: 403 } }));
    expect(result.state).toBe("permission");
    expect(result.data).toBeNull();
    expect(result.errorMessage).toBe("无权加载调试配置");
  });

  it("returns success and data for a published context", async () => {
    const published = { id: "v1" };
    const result = await loadAgentContext(() => Promise.resolve(published));
    expect(result).toEqual({ state: "success", data: published, errorMessage: "" });
  });

  it("returns empty only when the context loader resolves without data", async () => {
    const result = await loadAgentContext(() => Promise.resolve(null));
    expect(result).toEqual({ state: "empty", data: null, errorMessage: "" });
  });
});
