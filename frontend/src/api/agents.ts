import { request } from "./request";

export interface KnowledgeConfig {
  knowledge_base_ids: string[];
  top_k: number;
}

export interface Agent {
  id: string;
  name: string;
  description: string;
  model_id: string | null;
  version: string | null;
  knowledge_config?: KnowledgeConfig;
  status: string;
  published_version_id?: string | null;
  created_at: string;
}

export interface AgentVersion {
  id: string;
  agent_id: string;
  version: string;
  system_prompt: string;
  model_id: string;
  knowledge_config: KnowledgeConfig;
  created_at: string;
  is_published?: boolean;
}

export interface AgentCreatePayload {
  name: string;
  description: string;
  system_prompt: string;
  model_id: string;
  knowledge_config?: KnowledgeConfig;
}

export interface AgentVersionCreatePayload {
  system_prompt: string;
  model_id: string;
  knowledge_config?: KnowledgeConfig;
}

export async function listAgents() {
  return (await request.get<Agent[]>("/agents")).data;
}

export async function createAgent(payload: AgentCreatePayload) {
  return (await request.post<Agent>("/agents", payload)).data;
}

export async function listVersions(agentId: string) {
  return (await request.get<AgentVersion[]>(`/agents/${agentId}/versions`)).data;
}

export async function getPublishedVersion(agentId: string) {
  return (await request.get<AgentVersion>(`/agents/${agentId}/published-version`)).data;
}

export async function createVersion(agentId: string, payload: AgentVersionCreatePayload) {
  return (await request.post<AgentVersion>(`/agents/${agentId}/versions`, payload)).data;
}

export async function publishAgent(agentId: string, versionId: string) {
  return (await request.post<Agent>(`/agents/${agentId}/publish`, { version_id: versionId })).data;
}

export async function archiveAgent(agentId: string) {
  return (await request.post<Agent>(`/agents/${agentId}/archive`)).data;
}
