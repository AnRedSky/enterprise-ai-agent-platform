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
export async function getPublishedVersion(agentId) {
    return (await request.get(`/agents/${agentId}/published-version`)).data;
}
export async function createVersion(agentId, payload) {
    return (await request.post(`/agents/${agentId}/versions`, payload)).data;
}
export async function publishAgent(agentId, versionId) {
    return (await request.post(`/agents/${agentId}/publish`, { version_id: versionId })).data;
}
export async function archiveAgent(agentId) {
    return (await request.post(`/agents/${agentId}/archive`)).data;
}
