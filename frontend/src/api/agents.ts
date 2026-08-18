import { request } from "./request";

export interface Agent {
  id: string;
  name: string;
  description: string;
  system_prompt: string;
  model: string;
  version: string;
  status: string;
  created_at: string;
}

export async function listAgents() { return (await request.get<Agent[]>("/agents")).data; }
export async function createAgent(payload: { name: string; description: string; system_prompt: string; model: string }) { return (await request.post<Agent>("/agents", payload)).data; }
export async function executeAgent(id: string, input: string) { return (await request.post(`/agents/${id}/execute`, { input })).data; }
