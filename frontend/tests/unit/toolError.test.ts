import { describe, expect, it } from "vitest";
import { getToolUserError } from "../../src/utils/toolError";

describe("getToolUserError", () => {
  it("converts HTTP-style backend errors to a Chinese user message", () => {
    expect(getToolUserError(new Error("500 Internal Server Error"), "工具执行失败")).toBe("工具执行失败");
  });

  it("explains invalid JSON input without exposing parser details", () => {
    expect(getToolUserError(new SyntaxError("Unexpected token } in JSON"), "工具创建失败")).toBe(
      "输入结构不是有效的 JSON，请检查后重试",
    );
  });

  it("uses the provided Chinese fallback for unknown errors", () => {
    expect(getToolUserError(new Error("backend detail"), "工具数据加载失败，请稍后重试")).toBe(
      "工具数据加载失败，请稍后重试",
    );
    expect(getToolUserError("unknown", "工具状态更新失败，请稍后重试")).toBe("工具状态更新失败，请稍后重试");
  });
});
