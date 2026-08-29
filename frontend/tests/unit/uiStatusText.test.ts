import { describe, expect, it } from "vitest";

describe("页面状态文案规范", () => {
  const labels: Record<string, string> = {
    active: "已启用",
    inactive: "已停用",
    success: "成功",
    succeeded: "成功",
    failed: "失败",
    running: "运行中",
    pending: "等待中",
    completed: "已完成",
    cancelled: "已取消",
  };

  it("常见状态均使用中文用户文案", () => {
    for (const value of Object.values(labels)) expect(value).not.toMatch(/[A-Za-z]{2,}/);
  });

  it("未知状态不直接回显后端技术标识", () => {
    expect(labels["future_backend_status"]).toBeUndefined();
  });
});
