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
};
