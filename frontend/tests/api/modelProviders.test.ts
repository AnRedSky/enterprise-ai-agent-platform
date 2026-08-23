import { beforeEach, describe, expect, it, vi } from "vitest";

const { get, post, patch, del } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn() }));
vi.mock("axios", () => ({ default: { create: () => ({ get, post, patch, delete: del, interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } } }) } }));

import { createModelProfile, createModelProvider, deleteModelProfile, deleteModelProvider, listModelProfiles, listModelProviders, updateModelProfile, updateModelProvider } from "../../src/api/modelProviders";

describe("model providers api", () => {
  beforeEach(() => { get.mockReset(); post.mockReset(); patch.mockReset(); del.mockReset(); });
  it("lists organization scoped providers", async () => { get.mockResolvedValue({ data: { items: [], total: 0 } }); await listModelProviders("o1"); expect(get).toHaveBeenCalledWith("/model-providers?organization_id=o1&offset=0&limit=50"); });
  it("creates and updates a provider", async () => { post.mockResolvedValue({ data: { id: "p1" } }); patch.mockResolvedValue({ data: { id: "p1", name: "P2" } }); await createModelProvider({ organization_id: "o1", name: "P", provider_type: "ollama", provider_name: "local" }); await updateModelProvider("p1", { name: "P2" }); expect(post).toHaveBeenCalledWith("/model-providers", expect.objectContaining({ organization_id: "o1" })); expect(patch).toHaveBeenCalledWith("/model-providers/p1", { name: "P2" }); });
  it("manages profiles and preserves the backend route contract", async () => { get.mockResolvedValue({ data: [] }); post.mockResolvedValue({ data: { id: "m1" } }); patch.mockResolvedValue({ data: { id: "m1" } }); del.mockResolvedValue({ status: 204 }); await listModelProfiles("p1"); await createModelProfile("p1", { name: "Embedding", model_type: "embedding", model_name: "nomic-embed-text:latest", dimension: 768 }); await updateModelProfile("m1", { is_default: true }); await deleteModelProfile("m1"); expect(get).toHaveBeenCalledWith("/model-providers/p1/profiles"); expect(post).toHaveBeenCalledWith("/model-providers/p1/profiles", expect.objectContaining({ model_type: "embedding" })); expect(patch).toHaveBeenCalledWith("/model-providers/model-profiles/m1", { is_default: true }); expect(del).toHaveBeenCalledWith("/model-providers/model-profiles/m1"); });
  it("deletes a provider", async () => { del.mockResolvedValue({ status: 204 }); await deleteModelProvider("p1"); expect(del).toHaveBeenCalledWith("/model-providers/p1"); });
});
