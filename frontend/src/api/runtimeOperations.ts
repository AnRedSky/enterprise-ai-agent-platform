import { request } from "./request";

export type RuntimeOperationsOverview = {
  window_hours: number;
  since: string;
  generated_at: string;
  events: { total: number; status_counts: Record<string, number> };
  deliveries: { total: number; status_counts: Record<string, number>; retry_count: number; dead_letter_count: number };
  slo: { target_percent: number; delivery_success_percent: number; error_budget_percent: number; p95_delivery_latency_ms: number | null };
};

export type RuntimeProvider = {
  id: string; name: string; provider_type: string; enabled: boolean;
  config?: Record<string, unknown>; status?: string; last_checked_at?: string;
};

export type RuntimeProviderHealth = {
  provider_id: string; status: string; http_status?: number | null; latency_ms?: number | null; error?: string | null;
};

export type RuntimeAlertRule = {
  id: string; name: string; metric_name: string; operator: string; threshold: number;
  window_minutes: number; severity: string; enabled: boolean; created_at?: string; updated_at?: string;
};

export type RuntimeAlert = Record<string, unknown> & { id?: string; name?: string; status?: string; severity?: string; fired_at?: string; recovered_at?: string | null };
export type RuntimeMetricSample = Record<string, unknown> & { timestamp?: string; value?: number; metric_name?: string; dimension_key?: string | null; dimension_value?: string | null };
export type RuntimeAudit = Record<string, unknown> & { id?: string; action?: string; status?: string; actor_id?: string; created_at?: string };
export type RuntimeDeadLetter = Record<string, unknown> & { id: string; integration_event_id: string; attempt_count: number; response_status_code?: number | null; last_error_code?: string | null; last_error_message?: string | null; updated_at: string };

export type GlobalRuntimeExecution = {
  id: string; workflow_id: string; workflow_name: string; status: string;
  current_node_id?: string | null; worker_owner?: string | null; worker_attempt?: number | null;
  worker_lease_expires_at?: string | null; error_code?: string | null;
  started_at?: string | null; ended_at?: string | null; created_at: string;
};
export type GlobalRuntimePosture = {
  window_hours: number; since: string; generated_at: string;
  filters: { workflow_id?: string | null; agent_id?: string | null; trigger_id?: string | null; execution_id?: string | null; execution_status?: string | null };
  executions: { total: number; status_counts: Record<string, number>; active_count: number; recovery_count: number; items: GlobalRuntimeExecution[] };
  workflows: { total: number; status_counts: Record<string, number> };
  triggers: { total: number; status_counts: Record<string, number>; scheduled_enabled: number };
  worker: { liveness: "unknown" | "healthy" | "unhealthy"; liveness_reason_code?: string; running_frontiers: number; pending_frontiers: number; leased_frontiers: number; expired_leases: number; active_worker_owners: number };
  scheduler: { liveness: "unknown" | "healthy" | "unhealthy"; liveness_reason_code?: string; enabled_scheduled_triggers: number; durable_frontier_backlog: number };
};

type ListResponse<T> = { items: T[] };

export const runtimeOperationsApi = {
  overview(windowHours: number) { return request.get<RuntimeOperationsOverview>("/runtime/operations/overview", { params: { window_hours: windowHours } }); },
  global(params: { window_hours?: number; workflow_id?: string; agent_id?: string; trigger_id?: string; execution_id?: string; execution_status?: string; limit?: number } = {}) {
    return request.get<GlobalRuntimePosture>("/runtime/global", { params });
  },
  dimensions(windowHours: number) { return request.get<Record<string, unknown>>("/runtime/operations/dimensions", { params: { window_hours: windowHours } }); },
  alerts(windowHours: number) { return request.get<ListResponse<RuntimeAlert>>("/runtime/operations/alerts", { params: { window_hours: windowHours } }); },
  providers() { return request.get<ListResponse<RuntimeProvider>>("/runtime/operations/providers"); },
  setProviderEnabled(id: string, enabled: boolean) { return request.patch<RuntimeProvider>(`/runtime/operations/providers/${id}`, { enabled }); },
  probeProviderHealth(id: string) { return request.post<RuntimeProviderHealth>(`/runtime/operations/providers/${id}/health`); },
  alertRules() { return request.get<ListResponse<RuntimeAlertRule>>("/runtime/operations/alert-rules"); },
  setAlertRuleEnabled(id: string, enabled: boolean) { return request.patch<RuntimeAlertRule>(`/runtime/operations/alert-rules/${id}`, { enabled }); },
  evaluateAlertRules() { return request.post<{ items: RuntimeAlert[]; count: number }>("/runtime/operations/alert-rules/evaluate"); },
  createMetricsSnapshot() { return request.post<{ samples_written: number }>("/runtime/operations/metrics/snapshot"); },
  metricSeries(metricName: string, windowMinutes: number, dimensionKey?: string, dimensionValue?: string) {
    return request.get<{ items: RuntimeMetricSample[]; metric_name: string; window_minutes: number }>("/runtime/operations/metrics/series", { params: { metric_name: metricName, window_minutes: windowMinutes, dimension_key: dimensionKey, dimension_value: dimensionValue } });
  },
  audit(limit = 100) { return request.get<ListResponse<RuntimeAudit>>("/runtime/operations/audit", { params: { limit } }); },
  deadLetters(page: number, pageSize: number) { return request.get<{ items: RuntimeDeadLetter[]; page: number; page_size: number; total: number }>("/runtime/operations/dead-letters", { params: { page, page_size: pageSize } }); },
  replayDeadLetters(deliveryIds: string[]) { return request.post<{ replayed: string[]; rejected: Array<{ delivery_id: string; reason: string }> }>("/runtime/operations/dead-letters/replay", { delivery_ids: deliveryIds }); },
};
