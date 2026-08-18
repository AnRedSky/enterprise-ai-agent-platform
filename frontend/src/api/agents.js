import { request } from "./request";
export async function listAgents() {
    return (await request.get("/agents")).data;
}
export async function createAgent(payload) {
    return (await request.post("/agents", payload)).data;
}
export async function listVersions(agentId) {
    return (await request.get(`/agents/${agentId}/versions`)).data;
}
export async function createVersion(agentId, payload) {
    return (await request.post(`/agents/${agentId}/versions`, payload)).data;
}
