import { request } from "./request";

/**
 * Runtime 关联查询的最小 Execution 事实。
 * 后端只读 Contract 负责租户边界，前端不自行推导关联关系。
 */
export type RuntimeCorrelationExecution = {
  id: string;
  tenant_id: string;
  workflow_id: string;
  workflow_version_id: string;
  created_by: string;
  retry_of_execution_id: string | null;
  resume_of_execution_id: string | null;
  status: string;
  current_node_id: string | null;
  error_code: string | null;
  error_message: string | null;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
};

export type RuntimeCorrelationTrace = {
  id: string;
  tenant_id: string;
  execution_id: string;
  workflow_id: string;
  workflow_version_id: string;
  event_type: string;
  status: string;
  trace_id: string;
  actor_id: string | null;
  node_id?: string | null;
  data?: Record<string, unknown> | null;
  created_at: string;
};

export type RuntimeCorrelationAudit = {
  id: string;
  actor_id: string;
  tenant_id: string;
  workflow_id: string | null;
  workflow_version_id: string | null;
  workflow_execution_id: string | null;
  action: string;
  resource_type: string;
  resource_id: string;
  request_id: string | null;
  trace_id: string | null;
  status: string;
  error_code: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
};

export type RuntimeCorrelationOperatorAction = {
  id: string;
  tenant_id: string;
  actor_id: string;
  resource_type: string;
  resource_id: string;
  action: string;
  idempotency_key: string;
  status: string;
  result_resource_id: string | null;
  error_code: string | null;
  created_at: string;
  updated_at: string;
};

export type RuntimeCorrelationPage<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
};

export type RuntimeCorrelationResponse = {
  execution: RuntimeCorrelationExecution | null;
  traces: RuntimeCorrelationPage<RuntimeCorrelationTrace>;
  audits: RuntimeCorrelationPage<RuntimeCorrelationAudit>;
  operator_actions: RuntimeCorrelationOperatorAction[];
  focus_audit_id?: string | null;
  focus_operator_action_id?: string | null;
};

type CorrelationQuery = {
  trace_page?: number;
  trace_page_size?: number;
  audit_page?: number;
  audit_page_size?: number;
  trace_event_type?: string;
  trace_status?: string;
  audit_action?: string;
  audit_status?: string;
};

export const runtimeCorrelationsApi = {
  execution(id: string, query: CorrelationQuery = {}) {
    return request.get<RuntimeCorrelationResponse>(`/runtime/correlations/executions/${id}`, { params: query });
  },
  trace(id: string, query: CorrelationQuery = {}) {
    return request.get<RuntimeCorrelationResponse>(`/runtime/correlations/traces/${id}`, { params: query });
  },
  audit(id: string, query: CorrelationQuery = {}) {
    return request.get<RuntimeCorrelationResponse>(`/runtime/correlations/audits/${id}`, { params: query });
  },
  operatorAction(id: string, query: CorrelationQuery = {}) {
    return request.get<RuntimeCorrelationResponse>(`/runtime/correlations/operator-actions/${id}`, { params: query });
  },
};
