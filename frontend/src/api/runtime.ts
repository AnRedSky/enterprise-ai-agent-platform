import axios from "axios";
const client = axios.create({ baseURL: "/api/v1" });
export type Execution = { execution_id: string; request_id: string; trace_id: string; session_id?: string; agent_id: string; agent_version?: string; model_id?: string; status: string; started_at: string; ended_at?: string; duration_ms?: number; error_code?: string };
export type Event = { id: string; execution_id: string; trace_id: string; span_type: string; status: string; started_at: string; ended_at?: string; duration_ms?: number; model_id?: string; tool_id?: string; error_code?: string };
export const runtimeApi = {
  executions(params: Record<string, unknown>) { return client.get<{items: Execution[]; page: number; page_size: number; total: number}>("/runtime/executions", { params }); },
  executionEvents(id: string) { return client.get<{execution: Execution; items: Event[]}>(`/runtime/executions/${id}/events`); },
  auditLogs(params: Record<string, unknown>) { return client.get("/runtime/audit-logs", { params }); }
};
