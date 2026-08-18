import { request } from "./request";
export async function listTools() {
    return (await request.get("/tools")).data;
}
export async function createTool(payload) {
    return (await request.post("/tools", payload)).data;
}
export async function enableTool(id) {
    return (await request.post(`/tools/${id}/enable`)).data;
}
export async function disableTool(id) {
    return (await request.post(`/tools/${id}/disable`)).data;
}
export async function bindTool(toolId, agentId) {
    return (await request.post(`/tools/${toolId}/bind/${agentId}`)).data;
}
export async function unbindTool(toolId, agentId) {
    return (await request.delete(`/tools/${toolId}/bind/${agentId}`)).data;
}
export async function executeTool(toolId, agentId, arguments_) {
    return (await request.post(`/tools/${toolId}/execute`, {
        agent_id: agentId,
        arguments: arguments_,
    })).data;
}
