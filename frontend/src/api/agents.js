import { request } from "./request";
export async function listAgents() { return (await request.get("/agents")).data; }
export async function createAgent(payload) { return (await request.post("/agents", payload)).data; }
export async function executeAgent(id, input) { return (await request.post(`/agents/${id}/execute`, { input })).data; }
