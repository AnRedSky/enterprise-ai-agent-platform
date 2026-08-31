import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

describe("Workflow UI-04 state migration", () => {
  const source = readFileSync(resolve(process.cwd(), "src/views/workflows/index.vue"), "utf8");

  it("uses the shared state component for all five standard states", () => {
    expect(source).toContain('import StatePanel from "@/components/ui/StatePanel.vue"');
    expect(source).toContain('state="loading"');
    expect(source).toContain('state="empty"');
    expect(source).toContain('state="error"');
    expect(source).toContain('state="permission"');
    expect(source).toContain('state="success"');
  });

  it("keeps permission distinct from recoverable errors", () => {
    expect(source).toContain("httpStatus(error) === 403");
    expect(source).toContain("当前账号没有访问该资源的权限");
    expect(source).toContain('action-label="重试"');
  });

  it("preserves workflow success feedback and retry actions", () => {
    expect(source).toContain("function showSuccess(message: string)");
    expect(source).toContain("工作流创建成功");
    expect(source).toContain("工作流运行失败，请查看运行记录后重试");
  });
});
