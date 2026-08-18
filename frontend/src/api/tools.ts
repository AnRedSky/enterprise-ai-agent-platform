import { request } from "./request";

export interface Tool {
  id: string;
  name: string;
  description: string;
  endpoint: string | null;
  enabled: boolean;
  input_schema: Record<string, unknown>;
  created_at: string;
}

export interface ToolCreatePayload {
  name: string;
  description: string;
  endpoint?: string;
  enabled: boolean;
  input_schema: Record<string, unknown>;
}

export async function listTools() {
  return (await request.get<Tool[]>("/tools")).data;
}

export async function createTool(payload: ToolCreatePayload) {
  return (await request.post<Tool>("/tools", payload)).data;
}

export async function enableTool(id: string) {
  return (await request.post<{ id: string; enabled: boolean }>(`/tools/${id}/enable`)).data;
}

export async function disableTool(id: string) {
  return (await request.post<{ id: string; enabled: boolean }>(`/tools/${id}/disable`)).data;
}

export async function bindTool(toolId: string, agentId: string) {
  return (await request.post(`/tools/${toolId}/bind/${agentId}`)).data;
}

export async function unbindTool(toolId: string, agentId: string) {
  return (await request.delete(`/tools/${toolId}/bind/${agentId}`)).data;
}

export async function executeTool(toolId: string, agentId: string, arguments_: Record<string, unknown>) {
  return (
    await request.post(`/tools/${toolId}/execute`, {
      agent_id: agentId,
      arguments: arguments_,
    })
  ).data;
}
