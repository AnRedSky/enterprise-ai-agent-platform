import axios from "axios";

const client = axios.create({ baseURL: "/api/v1" });

export type Execution = {
  execution_id: string; request_id: string; trace_id: string; session_id?: string; agent_id?: string;
  agent_version?: string; model_id?: string; status: string; started_at: string; ended_at?: string;
  duration_ms?: number; error_code?: string;
};
export type Event = {
  id: string; execution_id: string; trace_id: string; span_type: string; status: string;
  started_at: string; ended_at?: string; duration_ms?: number; model_id?: string; tool_id?: string; error_code?: string;
};
export type AuditLog = {
  id: string; actor_id?: string; agent_id?: string; tool_id?: string; execution_id?: string;
  action: string; status: string; error_code?: string; created_at: string;
};
export type Page<T> = { items: T[]; page: number; page_size: number; total: number };
export type Timeline = { execution: Execution; items: Event[] };

export const runtimeApi = {
  executions(params: Record<string, unknown>) { return client.get<Page<Execution>>("/runtime/executions", { params }); },
  execution(id: string) { return client.get<Timeline>(`/runtime/executions/${id}`); },
  executionEvents(id: string) { return client.get<Timeline>(`/runtime/executions/${id}/events`); },
  auditLogs(params: Record<string, unknown>) { return client.get<Page<AuditLog>>("/runtime/audit-logs", { params }); },
};
