import { request } from "./request";
export const runtimeApi = {
    executions(params) { return request.get("/runtime/executions", { params }); },
    execution(id) { return request.get(`/runtime/executions/${id}`); },
    executionEvents(id) { return request.get(`/runtime/executions/${id}/events`); },
    auditLogs(params) { return request.get("/runtime/audit-logs", { params }); },
};
