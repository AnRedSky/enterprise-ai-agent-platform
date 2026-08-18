import { beforeEach, describe, expect, it, vi } from "vitest";

const { get, post, delete_: deleteMock } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), delete_: vi.fn() }));
vi.mock("axios", () => ({ default: { create: () => ({ get, post, delete: deleteMock, interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } } }) } }));

import { bindTool, disableTool, enableTool, executeTool, listTools, unbindTool } from "../../src/api/tools";

describe("tools api", () => {
  beforeEach(() => {
    get.mockReset();
    post.mockReset();
    deleteMock.mockReset();
  });

  it("lists tools", async () => {
    get.mockResolvedValue({ data: [{ id: "tool-1", name: "T", enabled: true }] });
    const result = await listTools();
    expect(result[0].id).toBe("tool-1");
    expect(get).toHaveBeenCalledWith("/tools");
  });

  it("controls enable/disable and binding", async () => {
    post.mockResolvedValue({ data: { enabled: true } });
    deleteMock.mockResolvedValue({ data: { enabled: false } });
    await enableTool("tool-1");
    await disableTool("tool-1");
    await bindTool("tool-1", "agent-1");
    await unbindTool("tool-1", "agent-1");
    expect(post).toHaveBeenNthCalledWith(1, "/tools/tool-1/enable");
    expect(post).toHaveBeenNthCalledWith(2, "/tools/tool-1/disable");
    expect(post).toHaveBeenNthCalledWith(3, "/tools/tool-1/bind/agent-1");
    expect(deleteMock).toHaveBeenCalledWith("/tools/tool-1/bind/agent-1");
  });

  it("executes a tool with an agent context", async () => {
    post.mockResolvedValue({ data: { execution_id: "execution-1", result: { ok: true } } });
    await executeTool("tool-1", "agent-1", { value: 1 });
    expect(post).toHaveBeenCalledWith("/tools/tool-1/execute", { agent_id: "agent-1", arguments: { value: 1 } });
  });
});
