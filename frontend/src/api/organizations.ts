import { request } from "./request";

export type OrganizationStatus = "active" | "suspended";
export type MembershipStatus = "active" | "suspended";
export type MembershipRole = "owner" | "admin" | "member";

export interface Organization {
  id: string;
  tenant_id: string;
  name: string;
  status: OrganizationStatus;
}

export interface OrganizationListResponse {
  items: Organization[];
  total: number;
}

export interface Membership {
  id: string;
  organization_id: string;
  user_id: string;
  status: MembershipStatus;
  role: MembershipRole;
}

export interface MembershipListResponse {
  items: Membership[];
  total: number;
}

export interface OrganizationCreatePayload { name: string }
export interface OrganizationUpdatePayload { name?: string; status?: OrganizationStatus }
export interface MembershipCreatePayload { user_id: string; role: "admin" | "member" }
export interface MembershipUpdatePayload { role?: "admin" | "member"; status?: MembershipStatus }

export async function listOrganizations(offset = 0, limit = 50) {
  return (await request.get<OrganizationListResponse>(`/organizations?offset=${offset}&limit=${limit}`)).data;
}
export async function createOrganization(payload: OrganizationCreatePayload) {
  return (await request.post<Organization>("/organizations", payload)).data;
}
export async function getOrganization(id: string) {
  return (await request.get<Organization>(`/organizations/${id}`)).data;
}
export async function updateOrganization(id: string, payload: OrganizationUpdatePayload) {
  return (await request.patch<Organization>(`/organizations/${id}`, payload)).data;
}
export async function listMembers(organizationId: string, offset = 0, limit = 50) {
  return (await request.get<MembershipListResponse>(`/organizations/${organizationId}/members?offset=${offset}&limit=${limit}`)).data;
}
export async function addMember(organizationId: string, payload: MembershipCreatePayload) {
  return (await request.post<Membership>(`/organizations/${organizationId}/members`, payload)).data;
}
export async function updateMember(organizationId: string, membershipId: string, payload: MembershipUpdatePayload) {
  return (await request.patch<Membership>(`/organizations/${organizationId}/members/${membershipId}`, payload)).data;
}
export async function transferOwner(organizationId: string, membershipId: string) {
  return (await request.post<Membership>(`/organizations/${organizationId}/members/${membershipId}/transfer-owner`)).data;
}
export async function removeMember(organizationId: string, membershipId: string) {
  await request.delete(`/organizations/${organizationId}/members/${membershipId}`);
}
