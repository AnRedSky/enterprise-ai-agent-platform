import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const source = readFileSync(resolve(root, "src/views/organizations/detail.vue"), "utf8");

describe("Organization detail presentation contract", () => {
  it("uses StatePanel for member loading instead of the forbidden v-loading directive", () => {
    expect(source).toContain("<template v-else-if=\"membersLoading\">");
    expect(source).toContain('<StatePanel state="loading" title="正在加载成员"');
    expect(source).not.toMatch(/\bv-loading\s*=/);
  });

  it("keeps shared presentation primitives and backend refresh semantics", () => {
    expect(source).toContain('import SurfaceCard from "@/components/ui/SurfaceCard.vue"');
    expect(source).toContain('import StatePanel from "@/components/ui/StatePanel.vue"');
    expect(source).toContain("await loadMembers(page)");
    expect(source).toContain("await loadMembers(Math.min(page, maxPage))");
    expect(source).not.toMatch(/<el-empty\b/);
    expect(source).not.toMatch(/<el-result\b/);
  });
});
