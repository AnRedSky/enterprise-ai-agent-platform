import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const read = (path: string) => readFileSync(resolve(root, path), "utf8");

describe("Audit and Dashboard consistency contract", () => {
  it("keeps Audit on shared primitives and clears stale records on failed reload", () => {
    const source = read("src/views/audit-log/components/AuditLogPanel.vue");
    expect(source).toContain("PageToolbar");
    expect(source).toContain("SurfaceCard");
    expect(source).toContain("StatePanel");
    expect(source).not.toMatch(/<el-card\b/);
    expect(source).not.toMatch(/\bv-loading\s*=/);
    expect(source).toContain("items.value = [];");
    expect(source).toContain("total.value = 0;");
    expect(source).toContain("execution_id: executionId");
    expect(source).toContain("row.execution_id");
  });

  it("keeps Dashboard free of raw state primitives and clears aggregate facts on reload failure", () => {
    const source = read("src/views/dashboard/components/DashboardOverview.vue");
    expect(source).toContain("PageHeader");
    expect(source).toContain("MetricCard");
    expect(source).toContain("SurfaceCard");
    expect(source).toContain("StatePanel");
    expect(source).not.toMatch(/<el-card\b/);
    expect(source).not.toMatch(/\bv-loading\s*=/);
    expect(source).not.toMatch(/<el-empty\b/);
    expect(source).toContain("function clearData()");
    expect(source).toContain("clearData();");
    expect(source).toContain("execution_id: executionId");
  });

  it("keeps dashboard navigation anchored to durable execution IDs", () => {
    const source = read("src/views/dashboard/components/DashboardOverview.vue");
    expect(source).toContain("function openExecution(executionId: string)");
    expect(source).toContain("query: { execution_id: executionId, source: \"dashboard\" }");
  });
});
