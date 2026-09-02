import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const read = (path: string) => readFileSync(resolve(root, path), "utf8");

describe("Dashboard consistency", () => {
  it("keeps the dashboard on shared UI patterns", () => {
    const view = read("src/views/dashboard/components/DashboardOverview.vue");
    for (const pattern of ["PageHeader", "StatePanel", "MetricCard", "SurfaceCard"]) {
      expect(view).toContain(pattern);
    }
  });

  it("deep-links recent executions by their durable execution_id", () => {
    const view = read("src/views/dashboard/components/DashboardOverview.vue");
    expect(view).toContain('query: { execution_id: executionId, source: "dashboard" }');
    expect(view).toContain("row.execution_id");
    expect(view).not.toContain("recentExecutions[0]");
  });
});
