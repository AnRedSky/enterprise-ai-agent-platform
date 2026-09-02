import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(__dirname, "../..");
const source = readFileSync(resolve(root, "src/views/runtime/components/RuntimeCorrelations.vue"), "utf8");

describe("RuntimeCorrelations UI consistency", () => {
  it("uses shared surface/state primitives instead of raw card and empty primitives", () => {
    expect(source).toContain('import StatePanel from "@/components/common/StatePanel.vue"');
    expect(source).toContain('import SurfaceCard from "@/components/common/SurfaceCard.vue"');
    expect(source).not.toContain("<el-card");
    expect(source).not.toContain("<el-empty");
    expect(source).toContain('state="loading"');
    expect(source).toContain('state="error"');
    expect(source).toContain('state="empty"');
  });

  it("keeps correlation navigation driven by durable backend facts", () => {
    expect(source).toContain("execution.id");
    expect(source).toContain("trace.trace_id");
    expect(source).toContain("audit.id");
    expect(source).toContain("audit.workflow_execution_id");
    expect(source).not.toMatch(/\b(?:executions|traces|audits|operator_actions)\s*\[\s*0\s*\]/);
  });

  it("clears stale correlation facts when a query fails", () => {
    expect(source).toContain("result.value = null");
    expect(source).toContain('error.value = "关联查询失败，可能对象不存在或不属于当前租户"');
  });
});
