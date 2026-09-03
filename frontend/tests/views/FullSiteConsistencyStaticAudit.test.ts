import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const viewsRoot = resolve(root, "src/views");

function collectVueFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) return collectVueFiles(path);
    return entry.isFile() && entry.name.endsWith(".vue") ? [path] : [];
  });
}

const files = collectVueFiles(viewsRoot);
const relative = (path: string) => path.replace(`${root}/`, "").replaceAll("\\", "/");

const forbiddenPresentationPatterns: Array<[string, RegExp]> = [
  ["raw Element Plus card", /<el-card\b/],
  ["v-loading directive", /\bv-loading\s*=/],
  ["raw Element Plus empty state", /<el-empty\b/],
  ["raw Element Plus result state", /<el-result\b/],
];

const forbiddenDurableFactPatterns: Array<[string, RegExp]> = [
  ["array-position entity inference", /\b(?:items|versions|destinations|providers|executions|triggers|workflows)\[0\]/],
  ["list ordering as relationship inference", /\b(?:items|rows|list|executions|traces|audits)\.(?:sort|reverse)\(/],
];

const forbiddenOptimisticPatterns: Array<[string, RegExp]> = [
  ["boolean optimistic toggle", /\b(?:row|item|provider|destination|subscription|trigger)\.enabled\s*=\s*!/],
  ["status optimistic toggle", /\b(?:row|item|trigger|provider|execution)\.status\s*=\s*!/],
];

describe("full-site static consistency audit", () => {
  it("keeps all views on shared state/card primitives", () => {
    for (const file of files) {
      const source = readFileSync(file, "utf8");
      for (const [label, pattern] of forbiddenPresentationPatterns) {
        expect(source, `${relative(file)}: ${label}`).not.toMatch(pattern);
      }
    }
  });

  it("keeps durable relationships independent of collection order", () => {
    for (const file of files) {
      const source = readFileSync(file, "utf8");
      for (const [label, pattern] of forbiddenDurableFactPatterns) {
        expect(source, `${relative(file)}: ${label}`).not.toMatch(pattern);
      }
    }
  });

  it("does not mutate durable status optimistically in view code", () => {
    for (const file of files) {
      const source = readFileSync(file, "utf8");
      for (const [label, pattern] of forbiddenOptimisticPatterns) {
        expect(source, `${relative(file)}: ${label}`).not.toMatch(pattern);
      }
    }
  });

  it("keeps Operations Console toggles backend-truth based", () => {
    const source = readFileSync(resolve(root, "src/views/integrations/OperationsConsole.vue"), "utf8");
    expect(source).toContain(":model-value=\"row.enabled\"");
    expect(source).toContain("@change=\"toggleProvider(row as RuntimeProvider, $event)\"");
    expect(source).toContain("@change=\"toggleRule(row as RuntimeAlertRule, $event)\"");
    expect(source).not.toContain("v-model=\"row.enabled\"");
    expect(source).not.toContain("Object.assign(row,r.data)");
    expect(source).toContain("await loadProviders()");
    expect(source).toContain("await loadAlerts()");
  });

  it("keeps Workflow Trigger mutations explicitly guarded and backend-truth based", () => {
    const source = readFileSync(resolve(root, "src/views/workflow-triggers/index.vue"), "utf8");
    expect(source).toContain("const actionKey = ref(\"\")");
    expect(source).toContain("actionKey.value = `toggle:${trigger.id}`");
    expect(source).toContain("actionKey.value = `delete:${trigger.id}`");
    expect(source).toContain("await loadTriggers()");
    expect(source).toContain("execution.value.id");
    expect(source).not.toContain("workflows.value[0]");
    expect(source).not.toContain("ElMessage.error(error instanceof Error ? error.message");
  });

  it("keeps Runtime Correlations on shared state/card primitives and durable facts", () => {
    const source = readFileSync(resolve(root, "src/views/runtime/components/RuntimeCorrelations.vue"), "utf8");
    expect(source).toContain('import StatePanel from "@/components/ui/StatePanel.vue"');
    expect(source).toContain('import SurfaceCard from "@/components/ui/SurfaceCard.vue"');
    expect(source).not.toContain("<el-card");
    expect(source).not.toContain("<el-empty");
    expect(source).toContain("execution.id");
    expect(source).toContain("trace.trace_id");
    expect(source).toContain("audit.id");
    expect(source).toContain("focusedAudit.workflow_execution_id");
  });

  it("keeps closed governance navigation anchored to durable IDs", () => {
    const operations = readFileSync(resolve(root, "src/views/integrations/OperationsConsole.vue"), "utf8");
    const correlation = readFileSync(resolve(root, "src/views/integrations/OperationsRuntimeCorrelation.vue"), "utf8");
    const audit = readFileSync(resolve(root, "src/views/audit-log/components/AuditLogPanel.vue"), "utf8");
    const dashboard = readFileSync(resolve(root, "src/views/dashboard/components/DashboardOverview.vue"), "utf8");
    expect(operations).toContain("execution_id:id");
    expect(correlation).toContain("audit.details?.workflow_execution_id");
    expect(audit).toContain("execution_id: executionId");
    expect(dashboard).toContain("execution_id: executionId");
  });
});
