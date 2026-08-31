import { request } from "./request";

export type RuntimeLiveness = string;

export type RuntimeWorkerOwner = {
  worker_owner: string;
  claim_count: number;
};

export type RuntimeWorkerError = {
  id: string;
  execution_id: string;
  status: string;
  attempt: number;
  worker_owner: string | null;
  worker_lease_expires_at: string | null;
  error_code: string;
  created_at: string;
};

export type RuntimeWorkerDiagnostics = {
  window_hours: number;
  generated_at: string;
  liveness: RuntimeLiveness;
  liveness_reason_code: string;
  frontier: {
    total: number;
    status_counts: Record<string, number>;
    running: number;
    pending: number;
    completed: number;
    failed: number;
  };
  leases: {
    without_expiry: number;
    active: number;
    expired: number;
  };
  owners: RuntimeWorkerOwner[];
  recent_errors: RuntimeWorkerError[];
};

export type RuntimeSchedulerTrigger = {
  id: string;
  workflow_id: string;
  name: string;
  status: string;
  config: Record<string, unknown>;
  updated_at: string;
};

export type RuntimeSchedulerDiagnostics = {
  generated_at: string;
  liveness: RuntimeLiveness;
  liveness_reason_code: string;
  durable: {
    enabled_scheduled_triggers: number;
    disabled_scheduled_triggers: number;
    pending_frontier_items: number;
  };
  triggers: RuntimeSchedulerTrigger[];
};

export const runtimeDiagnosticsApi = {
  worker(windowHours = 24, limit = 50) {
    return request.get<RuntimeWorkerDiagnostics>("/runtime/diagnostics/worker", {
      params: { window_hours: windowHours, limit },
    });
  },
  scheduler(limit = 50) {
    return request.get<RuntimeSchedulerDiagnostics>("/runtime/diagnostics/scheduler", {
      params: { limit },
    });
  },
};
