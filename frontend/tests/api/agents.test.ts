import { beforeEach, describe, expect, it, vi } from "vitest";

const { get, post } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock("axios", () => ({ default: { create: () => ({ get, post, interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } } }) } }));

import { createAgent, createVersion, listAgents, listVersions } from "../../src/api/agents";

describe("agents api", () => {
  beforeEach(() => {
    get.mockReset();
    post.mockReset();
  });

  it("lists agents with latest version metadata", async () => {
    get.mockResolvedValue({ data: [{ id: "agent-1", name: "A", model_id: "mock-model", version: "1.0.0", status: "draft", description: "", created_at: "" }] });
    const result = await listAgents();
    expect(result[0].version).toBe("1.0.0");
    expect(get).toHaveBeenCalledWith("/agents");
  });

  it("creates agents and versions", async () => {
    post.mockResolvedValue({ data: { id: "agent-1", version: "1.1.0" } });
    await createAgent({ name: "A", description: "", system_prompt: "You are A", model_id: "mock-model" });
    await createVersion("agent-1", { system_prompt: "v2", model_id: "mock-model" });
    expect(post).toHaveBeenNthCalledWith(1, "/agents", expect.any(Object));
    expect(post).toHaveBeenNthCalledWith(2, "/agents/agent-1/versions", { system_prompt: "v2", model_id: "mock-model" });
  });

  it("loads versions for an agent", async () => {
    get.mockResolvedValue({ data: [{ id: "v1", agent_id: "agent-1", version: "1.0.0", system_prompt: "A", model_id: "mock-model", created_at: "" }] });
    await listVersions("agent-1");
    expect(get).toHaveBeenCalledWith("/agents/agent-1/versions");
  });
});
