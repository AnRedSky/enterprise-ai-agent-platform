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
});
