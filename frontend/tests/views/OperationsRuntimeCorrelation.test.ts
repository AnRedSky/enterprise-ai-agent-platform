import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const read = (path: string) => readFileSync(resolve(root, path), "utf8");

describe("Operations Runtime durable correlation", () => {
  it("uses an explicit workflow_execution_id fact from the audit payload", () => {
    const source = read("src/views/integrations/OperationsRuntimeCorrelation.vue");
    expect(source).toContain("audit.details?.workflow_execution_id");
    expect(source).toContain("typeof value === \"string\"");
    expect(source).not.toContain("items[0]");
    expect(source).not.toContain("sort(");
  });

  it("opens Runtime with the durable execution_id instead of an inferred row", () => {
    const source = read("src/views/integrations/OperationsRuntimeCorrelation.vue");
    expect(source).toContain('query: { execution_id: executionId, source: "runtime-operations-audit" }');
    expect(source).toContain("runtimeOperationsApi.auditQuery");
  });

  it("clears stale correlation rows before reload and exposes permission/error states", () => {
    const source = read("src/views/integrations/OperationsRuntimeCorrelation.vue");
    expect(source).toContain("rows.value = []");
    expect(source).toContain('state.value = error?.response?.status === 403 ? "permission" : "error"');
    expect(source).toContain('state="error"');
    expect(source).toContain('state="permission"');
    expect(source).toContain('state="empty"');
  });
});
