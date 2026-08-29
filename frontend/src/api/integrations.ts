import { request } from "./request";

export interface WebhookDestination {
  id: string;
  tenant_id: string;
  name: string;
  endpoint_url: string;
  secret_ref: string | null;
  headers: Record<string, string>;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface WebhookSubscription {
  id: string;
  tenant_id: string;
  destination_id: string;
  event_type: string;
  priority: number;
  enabled: boolean;
  filter_config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface WebhookDelivery {
  id: string;
  tenant_id: string;
  subscription_id: string;
  destination_id: string;
  integration_event_id: string;
  status: string;
  attempt_count: number;
  next_attempt_at: string | null;
  last_attempt_at: string | null;
  delivered_at: string | null;
  response_status_code: number | null;
  last_error_code: string | null;
  last_error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface WebhookDeliveryAudit {
  id: string;
  delivery_id: string;
  integration_event_id: string;
  action: string;
  attempt_count: number;
  status: string;
  response_status_code: number | null;
  error_code: string | null;
  error_message: string | null;
  actor: string;
  created_at: string;
}

export interface WebhookDestinationCreatePayload {
  name: string;
  endpoint_url: string;
  secret_ref?: string;
  headers?: Record<string, string>;
}

export interface WebhookSubscriptionCreatePayload {
  destination_id: string;
  event_type: string;
  priority?: number;
  filter_config?: Record<string, unknown>;
}

export const integrationApi = {
  destinations() {
    return request.get<WebhookDestination[]>("/webhooks/destinations");
  },
  createDestination(payload: WebhookDestinationCreatePayload) {
    return request.post<WebhookDestination>("/webhooks/destinations", payload);
  },
  subscriptions() {
    return request.get<WebhookSubscription[]>("/webhooks/subscriptions");
  },
  createSubscription(payload: WebhookSubscriptionCreatePayload) {
    return request.post<WebhookSubscription>("/webhooks/subscriptions", payload);
  },
  deliveries(params?: Record<string, unknown>) {
    return request.get<WebhookDelivery[]>("/webhooks/deliveries", { params });
  },
  deliveryAudit(deliveryId: string, params?: Record<string, unknown>) {
    return request.get<WebhookDeliveryAudit[]>(`/webhooks/deliveries/${deliveryId}/audit`, { params });
  },
  replayDelivery(deliveryId: string) {
    return request.post<WebhookDelivery>(`/webhooks/deliveries/${deliveryId}/replay`);
  },
};
