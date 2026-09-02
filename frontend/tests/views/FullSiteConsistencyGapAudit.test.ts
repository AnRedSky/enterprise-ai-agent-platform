import { describe, expect, it } from "vitest";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const read = (path: string) => readFileSync(resolve(root, path), "utf8");

const coreViews = [
  "src/views/workflows/index.vue",
  "src/views/workflows/WorkflowLifecycle.vue",
  "src/views/runtime/index.vue",
  "src/views/agents/index.vue",
  "src/views/knowledge/index.vue",
  "src/views/tools/index.vue",
  "src/views/organizations/index.vue",
  "src/views/organizations/detail.vue",
  "src/views/organizations/model-providers.vue",
  "src/views/integrations/index.vue",
  "src/views/integrations/OperationsConsoleWorkbench.vue",
  "src/views/audit-log/AuditLogWorkbench.vue",
  "src/views/dashboard/index.vue",
];

describe("full-site UI consistency gap audit", () => {
  it("keeps the core P0/P1 view inventory present", () => {
    for (const view of coreViews) expect(existsSync(resolve(root, view)), view).toBe(true);
  });

  it("does not reintroduce known durable-fact inference patterns", () => {
    for (const view of coreViews) {
      const source = read(view);
      expect(source, view).not.toMatch(/\b(items|versions|destinations|providers|executions)\[0\]/);
      expect(source, view).not.toMatch(/\b(list|rows|items)\.(sort|reverse)\(/);
    }
  });

  it("keeps Operations, Audit and Dashboard on real-ID navigation", () => {
    const operations = read("src/views/integrations/OperationsConsole.vue");
    const correlation = read("src/views/integrations/OperationsRuntimeCorrelation.vue");
    const audit = read("src/views/audit-log/components/AuditLogPanel.vue");
    const dashboard = read("src/views/dashboard/components/DashboardOverview.vue");
    expect(operations).toContain("execution_id:id");
    expect(correlation).toContain("audit.details?.workflow_execution_id");
    expect(audit).toContain("execution_id:executionId");
    expect(dashboard).toContain("execution_id: executionId");
  });

  it("requires shared state primitives on the newly closed governance pages", () => {
    for (const view of [
      "src/views/integrations/OperationsConsole.vue",
      "src/views/integrations/OperationsRuntimeCorrelation.vue",
      "src/views/audit-log/AuditLogWorkbench.vue",
      "src/views/dashboard/components/DashboardOverview.vue",
    ]) {
      const source = read(view);
      expect(source, view).toContain("StatePanel");
    }
  });
});
