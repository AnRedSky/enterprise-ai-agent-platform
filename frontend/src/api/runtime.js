import axios from "axios";
const client = axios.create({ baseURL: "/api/v1" });
export const runtimeApi = {
    executions(params) { return client.get("/runtime/executions", { params }); },
    execution(id) { return client.get(`/runtime/executions/${id}`); },
    executionEvents(id) { return client.get(`/runtime/executions/${id}/events`); },
    auditLogs(params) { return client.get("/runtime/audit-logs", { params }); },
};
