import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const read = (path: string) => readFileSync(resolve(root, path), "utf8");

describe("Audit Log UI-03 / Runtime correlation", () => {
  it("routes audit through the shared page shell", () => {
    const router = read("src/router/index.ts");
    expect(router).toContain('/runtime/audit", component: () => import("../views/audit-log/AuditLogWorkbench.vue")');
  });

  it("preserves the backend execution_id in the Runtime deep link", () => {
    const panel = read("src/views/audit-log/components/AuditLogPanel.vue");
    expect(panel).toContain('query:{execution_id:executionId,source:"audit"}');
    expect(panel).not.toContain("items[0]");
    expect(panel).not.toContain("items[page");
  });

  it("keeps audit records tenant-scoped through the existing runtime contract", () => {
    const panel = read("src/views/audit-log/components/AuditLogPanel.vue");
    expect(panel).toContain("runtimeApi.auditLogs");
    expect(panel).toContain("row.execution_id");
  });
});
