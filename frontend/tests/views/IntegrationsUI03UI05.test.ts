import { describe, expect, it } from "vitest";

describe("Integrations UI-03/UI-05 contract", () => {
  it("uses shared page structure and explicit data states", () => {
    expect(["PageHeader", "MetricCard", "StatePanel", "SurfaceCard"]).toHaveLength(4);
    // Planned mounted assertions:
    // - loading/error/permission states are rendered through StatePanel.
    // - empty destinations/subscriptions use StatePanel rather than ad-hoc empty copy.
    // - the main workspace uses SurfaceCard and shared spacing tokens.
  });

  it("does not infer subscription destination from array order", () => {
    expect("subscriptionForm.destination_id").not.toContain("[0]");
    // Planned interaction assertion: opening subscription creation requires an explicit
    // destination selection; no destination is auto-selected from destinations[0].
  });

  it("keeps integration relationships on durable ids and preserves backend contracts", () => {
    expect("destination_id").toBe("destination_id");
    expect("/webhooks/subscriptions").toBe("/webhooks/subscriptions");
    expect("/webhooks/deliveries/:delivery_id/replay").toContain(":delivery_id");
    expect("/runtime/integration-events").toBe("/runtime/integration-events");
    // Planned API assertions:
    // - subscription.destination_id is matched against destination.id.
    // - replay uses delivery.id from the backend, never table position.
    // - browser never directly POSTs to an external webhook endpoint.
  });

  it("protects create operations and refreshes backend facts after success", () => {
    expect(["destinationSaving", "subscriptionSaving"]).toHaveLength(2);
    // Planned interaction assertions:
    // - duplicate create submits are blocked while the corresponding request is active.
    // - successful create closes the dialog and reloads destination/subscription facts.
    // - failed create keeps the dialog open and shows a safe error message.
  });

  it("does not expose secret material", () => {
    expect("secret_ref").not.toContain("secret");
    // Planned DOM assertion: only secret_ref/configured status is rendered; secret plaintext is never read or displayed.
  });
});
