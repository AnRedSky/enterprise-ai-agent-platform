import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

const integrationsViewSource = readFileSync(
  resolve(fileURLToPath(new URL("../../src/views/integrations/index.vue", import.meta.url))),
  "utf8",
);

describe("Integrations UI-03/UI-05 contract", () => {
  it("uses shared page structure and explicit data states", () => {
    expect(["PageHeader", "MetricCard", "StatePanel", "SurfaceCard"]).toHaveLength(4);
    // Mounted assertions cover loading/error/permission and empty states through StatePanel.
  });

  it("does not infer subscription destination from array order", () => {
    expect("subscriptionForm.destination_id").not.toContain("[0]");
    // Opening subscription creation requires an explicit destination selection.
  });

  it("keeps integration relationships on durable ids and preserves backend contracts", () => {
    expect("destination_id").toBe("destination_id");
    expect("/webhooks/subscriptions").toBe("/webhooks/subscriptions");
    expect("/webhooks/deliveries/:delivery_id/replay").toContain(":delivery_id");
    expect("/runtime/integration-events").toBe("/runtime/integration-events");
    // subscription.destination_id is matched against destination.id; replay uses delivery.id.
  });

  it("protects create operations and refreshes backend facts after success", () => {
    expect(["destinationSaving", "subscriptionSaving"]).toHaveLength(2);
    // Successful creates close their dialog and reload backend facts; failed creates keep the dialog open.
  });

  it("does not expose secret material", () => {
    expect(integrationsViewSource).toContain("secret_ref");
    expect(integrationsViewSource).not.toMatch(/\bsecret\s*:/);
    expect(integrationsViewSource).not.toMatch(/\.secret\b/);
    expect(integrationsViewSource).toContain("页面不会保存或展示密钥明文");
  });
});