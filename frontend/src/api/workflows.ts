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

export type WorkflowExecution = {
  id: string;
  tenant_id: string;
  workflow_id: string;
  workflow_version_id: string;
  created_by: string;
  retry_of_execution_id?: string;
  idempotency_key?: string;
  status: string;
  current_node_id?: string;
  input_data: Record<string, unknown>;
  output_data?: Record<string, unknown>;
  error_code?: string;
  error_message?: string;
  started_at?: string;
  ended_at?: string;
  created_at: string;
};

export type WorkflowExecutionNode = {
  id: string;
  execution_id: string;
  node_id: string;
  status: string;
  attempt: number;
  input_data?: Record<string, unknown>;
  output_data?: Record<string, unknown>;
  error_code?: string;
  error_message?: string;
  started_at?: string;
  ended_at?: string;
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

export type WorkflowTriggerType = "manual" | "scheduled";
export type WorkflowTriggerStatus = "enabled" | "disabled";

export type ScheduledTriggerConfig = {
  timezone: string;
  interval_seconds: number;
};

export type WorkflowTrigger = {
  id: string;
  tenant_id: string;
  workflow_id: string;
  name: string;
  trigger_type: WorkflowTriggerType;
  status: WorkflowTriggerStatus;
  config: Record<string, unknown>;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export const workflowApi = {
  list() { return request.get<Workflow[]>("/workflows"); },
  create(payload: { name: string; description: string }) { return request.post<Workflow>("/workflows", payload); },
  update(id: string, payload: { name?: string; description?: string }) { return request.patch<Workflow>(`/workflows/${id}`, payload); },
  versions(id: string) { return request.get<WorkflowVersion[]>(`/workflows/${id}/versions`); },
  createVersion(id: string, definition: Record<string, unknown>) { return request.post<WorkflowVersion>(`/workflows/${id}/versions`, { definition }); },
  publish(id: string, versionId: string) { return request.post<WorkflowVersion>(`/workflows/${id}/versions/${versionId}/publish`); },
  triggers(id: string) { return request.get<WorkflowTrigger[]>(`/workflows/${id}/triggers`); },
  createTrigger(id: string, payload: { name: string; trigger_type: WorkflowTriggerType; config: Record<string, unknown> }) {
    return request.post<WorkflowTrigger>(`/workflows/${id}/triggers`, payload);
  },
  updateTrigger(id: string, triggerId: string, payload: { name?: string; status?: WorkflowTriggerStatus; config?: Record<string, unknown> }) {
    return request.patch<WorkflowTrigger>(`/workflows/${id}/triggers/${triggerId}`, payload);
  },
  deleteTrigger(id: string, triggerId: string) { return request.delete<void>(`/workflows/${id}/triggers/${triggerId}`); },
  invokeTrigger(id: string, triggerId: string, inputData: Record<string, unknown> = {}, idempotencyKey?: string) {
    return request.post<WorkflowExecution>(
      `/workflows/${id}/triggers/${triggerId}/invoke`,
      { input_data: inputData },
      idempotencyKey ? { headers: { "Idempotency-Key": idempotencyKey } } : undefined,
    );
  },
  createExecution(workflowId: string, inputData: Record<string, unknown> = {}, idempotencyKey?: string) {
    return request.post<WorkflowExecution>(
      `/workflows/${workflowId}/executions`,
      { input_data: inputData },
      idempotencyKey ? { headers: { "Idempotency-Key": idempotencyKey } } : undefined,
    );
  },
  runExecution(executionId: string) { return request.post<WorkflowExecution>(`/workflows/executions/${executionId}/run`); },
  cancelExecution(executionId: string, reason?: string) {
    return request.post<WorkflowExecution>(`/workflows/executions/${executionId}/cancel`, { reason });
  },
  retryExecution(executionId: string) {
    return request.post<WorkflowExecution>(`/workflows/executions/${executionId}/retry`);
  },
  execution(executionId: string) { return request.get<WorkflowExecution>(`/workflows/executions/${executionId}`); },
  executionNodes(executionId: string) { return request.get<WorkflowExecutionNode[]>(`/workflows/executions/${executionId}/nodes`); },
  trace(executionId: string) { return request.get<{ execution_id: string; items: WorkflowTrace[] }>(`/runtime/executions/${executionId}/trace`); },
  audit(params: Record<string, unknown>) { return request.get<{ items: Array<Record<string, unknown>>; page: number; page_size: number; total: number }>("/runtime/audit-logs", { params }); },
};
