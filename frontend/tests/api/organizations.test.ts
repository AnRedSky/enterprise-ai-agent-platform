import { beforeEach, describe, expect, it, vi } from "vitest";

const { get, post, patch, del } = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), del: vi.fn() }));
vi.mock("axios", () => ({ default: { create: () => ({ get, post, patch, delete: del, interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } } }) } }));

import { addMember, createOrganization, getOrganization, listMembers, listOrganizations, removeMember, transferOwner, updateMember, updateOrganization } from "../../src/api/organizations";

describe("organizations api", () => {
  beforeEach(() => { get.mockReset(); post.mockReset(); patch.mockReset(); del.mockReset(); });

  it("lists organizations", async () => { get.mockResolvedValue({ data: { items: [{ id: "o1", tenant_id: "t1", name: "Acme", status: "active" }], total: 1 } }); const result = await listOrganizations(); expect(result.total).toBe(1); expect(get).toHaveBeenCalledWith("/organizations?offset=0&limit=50"); });
  it("creates an organization", async () => { post.mockResolvedValue({ data: { id: "o1", name: "Acme" } }); await createOrganization({ name: "Acme" }); expect(post).toHaveBeenCalledWith("/organizations", { name: "Acme" }); });
  it("gets and updates an organization", async () => { get.mockResolvedValue({ data: { id: "o1", name: "Acme", status: "active" } }); patch.mockResolvedValue({ data: { id: "o1", name: "Acme 2", status: "suspended" } }); expect((await getOrganization("o1")).id).toBe("o1"); await updateOrganization("o1", { name: "Acme 2", status: "suspended" }); expect(patch).toHaveBeenCalledWith("/organizations/o1", { name: "Acme 2", status: "suspended" }); });
  it("lists members", async () => { get.mockResolvedValue({ data: { items: [], total: 0 } }); await listMembers("o1"); expect(get).toHaveBeenCalledWith("/organizations/o1/members?offset=0&limit=50"); });
  it("adds a member", async () => { post.mockResolvedValue({ data: { id: "m1", user_id: "u1", role: "member" } }); await addMember("o1", { user_id: "u1", role: "member" }); expect(post).toHaveBeenCalledWith("/organizations/o1/members", { user_id: "u1", role: "member" }); });
  it("updates a member", async () => { patch.mockResolvedValue({ data: { id: "m1", role: "admin" } }); await updateMember("o1", "m1", { role: "admin" }); expect(patch).toHaveBeenCalledWith("/organizations/o1/members/m1", { role: "admin" }); });
  it("transfers ownership through the dedicated endpoint", async () => { post.mockResolvedValue({ data: { id: "m2", role: "owner" } }); await transferOwner("o1", "m2"); expect(post).toHaveBeenCalledWith("/organizations/o1/members/m2/transfer-owner"); });
  it("removes a member", async () => { del.mockResolvedValue({ status: 204 }); await removeMember("o1", "m1"); expect(del).toHaveBeenCalledWith("/organizations/o1/members/m1"); });
});
