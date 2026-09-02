import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const read = (path: string) => readFileSync(resolve(root, path), "utf8");

describe("Operations Console UI-03/UI-04/UI-05", () => {
  it("routes through the shared PageHeader shell", () => {
    const router = read("src/router/index.ts");
    const shell = read("src/views/integrations/OperationsConsoleWorkbench.vue");
    expect(router).toContain("OperationsConsoleWorkbench.vue");
    expect(shell).toContain("PageHeader");
    expect(shell).toContain("OperationsRuntimeCorrelation");
  });
  it("uses shared state panels for independently loaded workbenches", () => {
    const source = read("src/views/integrations/OperationsConsole.vue");
    for (const state of ["loading", "error", "empty"]) expect(source).toContain(`state=\"${state}\"`);
    for (const loader of ["loadGlobal", "loadOverview", "loadAlerts", "loadProviders", "loadAudit", "loadMetrics", "loadDeadLetters"]) expect(source).toContain(loader);
  });
  it("protects high-impact actions and refreshes backend truth after mutation", () => {
    const source = read("src/views/integrations/OperationsConsole.vue");
    expect(source).toContain("ElMessageBox.confirm");
    expect(source).toContain("if(replayingId.value)return");
    expect(source).toContain("if(togglingProviderId.value)return");
    expect(source).toContain("if(togglingRuleId.value)return");
    expect(source).toContain("await loadProviders()");
    expect(source).toContain("await loadAlerts()");
    expect(source).toContain("await loadDeadLetters()");
  });
});
