import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const read = (path: string) => readFileSync(resolve(root, path), "utf8");

describe("Operations Console UI-03 shared shell", () => {
  it("routes /runtime/operations through the shared page shell", () => {
    const router = read("src/router/index.ts");
    expect(router).toContain('/runtime/operations", component: () => import("../views/integrations/OperationsConsoleWorkbench.vue")');
  });

  it("uses PageHeader and preserves the existing operations sub-workbench", () => {
    const shell = read("src/views/integrations/OperationsConsoleWorkbench.vue");
    expect(shell).toContain('import PageHeader from "@/components/ui/PageHeader.vue"');
    expect(shell).toContain("<PageHeader");
    expect(shell).toContain('import OperationsConsole from "./OperationsConsole.vue"');
    expect(shell).toContain("<OperationsConsole />");
  });
});
