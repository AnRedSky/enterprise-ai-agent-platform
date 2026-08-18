import { request } from "./request";

export interface Agent {
  id: string;
  name: string;
  description: string;
  model_id: string | null;
  version: string | null;
  status: string;
  created_at: string;
}

export interface AgentVersion {
  id: string;
  agent_id: string;
  version: string;
  system_prompt: string;
  model_id: string;
  created_at: string;
}

export interface AgentCreatePayload {
  name: string;
  description: string;
  system_prompt: string;
  model_id: string;
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

export async function createVersion(agentId: string, payload: Pick<AgentVersion, "system_prompt" | "model_id">) {
  return (await request.post<AgentVersion>(`/agents/${agentId}/versions`, payload)).data;
}
