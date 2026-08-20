import { request } from "./request";

export type Workflow = {
  id: string;
  name: string;
  description: string;
  owner_id: string;
  tenant_id: string;
  status: string;
  published_version_id?: string;
  created_at: string;
  updated_at: string;
};

export type WorkflowVersion = {
  id: string;
  workflow_id: string;
  version: number;
  definition: Record<string, unknown>;
  status: string;
  created_by: string;
  created_at: string;
};

export type WorkflowTrace = {
  id: string;
  execution_id: string;
  workflow_id: string;
  workflow_version_id: string;
  node_id?: string;
  event_type: string;
  status: string;
  trace_id: string;
  actor_id?: string;
  data?: Record<string, unknown>;
  error_code?: string;
  error_message?: string;
  created_at: string;
};

export const workflowApi = {
  list() { return request.get<Workflow[]>("/workflows"); },
  create(payload: { name: string; description: string }) { return request.post<Workflow>("/workflows", payload); },
  update(id: string, payload: { name?: string; description?: string }) { return request.patch<Workflow>(`/workflows/${id}`, payload); },
  versions(id: string) { return request.get<WorkflowVersion[]>(`/workflows/${id}/versions`); },
  createVersion(id: string, definition: Record<string, unknown>) { return request.post<WorkflowVersion>(`/workflows/${id}/versions`, { definition }); },
  publish(id: string, versionId: string) { return request.post<WorkflowVersion>(`/workflows/${id}/versions/${versionId}/publish`); },
  trace(executionId: string) { return request.get<{ execution_id: string; items: WorkflowTrace[] }>(`/runtime/executions/${executionId}/trace`); },
  audit(params: Record<string, unknown>) { return request.get<{ items: Array<Record<string, unknown>>; page: number; page_size: number; total: number }>("/runtime/audit-logs", { params }); },
};
