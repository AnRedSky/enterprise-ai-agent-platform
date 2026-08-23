import { request } from "./request";

export type ModelType = "chat" | "embedding";

export interface ModelProvider {
  id: string;
  organization_id: string;
  name: string;
  provider_type: string;
  provider_name: string;
  endpoint: string | null;
  credential_ref: string | null;
  enabled: boolean;
  metadata: Record<string, unknown>;
}

export interface ModelProviderListResponse { items: ModelProvider[]; total: number }
export interface ModelProviderCreatePayload {
  organization_id: string;
  name: string;
  provider_type: string;
  provider_name: string;
  endpoint?: string | null;
  credential_ref?: string | null;
  enabled?: boolean;
  metadata?: Record<string, unknown>;
}
export interface ModelProviderUpdatePayload {
  name?: string;
  endpoint?: string | null;
  credential_ref?: string | null;
  enabled?: boolean;
  metadata?: Record<string, unknown>;
}

export interface ModelProfile {
  id: string;
  provider_id: string;
  name: string;
  model_type: ModelType;
  model_name: string;
  dimension: number | null;
  capabilities: Record<string, unknown>;
  parameters: Record<string, unknown>;
  enabled: boolean;
  is_default: boolean;
}
export interface ModelProfileCreatePayload {
  name: string;
  model_type: ModelType;
  model_name: string;
  dimension?: number | null;
  capabilities?: Record<string, unknown>;
  parameters?: Record<string, unknown>;
  enabled?: boolean;
  is_default?: boolean;
}
export interface ModelProfileUpdatePayload {
  name?: string;
  model_name?: string;
  dimension?: number | null;
  capabilities?: Record<string, unknown>;
  parameters?: Record<string, unknown>;
  enabled?: boolean;
  is_default?: boolean;
}

export async function listModelProviders(organizationId: string, offset = 0, limit = 50) {
  return (await request.get<ModelProviderListResponse>(`/model-providers?organization_id=${organizationId}&offset=${offset}&limit=${limit}`)).data;
}
export async function createModelProvider(payload: ModelProviderCreatePayload) {
  return (await request.post<ModelProvider>("/model-providers", payload)).data;
}
export async function updateModelProvider(id: string, payload: ModelProviderUpdatePayload) {
  return (await request.patch<ModelProvider>(`/model-providers/${id}`, payload)).data;
}
export async function deleteModelProvider(id: string) {
  await request.delete(`/model-providers/${id}`);
}
export async function listModelProfiles(providerId: string) {
  return (await request.get<ModelProfile[]>(`/model-providers/${providerId}/profiles`)).data;
}
export async function createModelProfile(providerId: string, payload: ModelProfileCreatePayload) {
  return (await request.post<ModelProfile>(`/model-providers/${providerId}/profiles`, payload)).data;
}
export async function updateModelProfile(id: string, payload: ModelProfileUpdatePayload) {
  return (await request.patch<ModelProfile>(`/model-providers/model-profiles/${id}`, payload)).data;
}
export async function deleteModelProfile(id: string) {
  await request.delete(`/model-providers/model-profiles/${id}`);
}
