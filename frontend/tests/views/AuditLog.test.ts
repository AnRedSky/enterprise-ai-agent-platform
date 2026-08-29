import { describe, expect, it, vi, beforeEach } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";

const { auditLogs } = vi.hoisted(() => ({ auditLogs: vi.fn() }));
vi.mock("../../src/api/runtime", () => ({ runtimeApi: { auditLogs } }));
vi.mock("element-plus", () => ({ ElMessage: { error: vi.fn() } }));

import AuditLog from "../../src/views/audit-log/components/AuditLogPanel.vue";

const stubs = {
  "el-card": { template: "<div><slot name=\"header\"/><slot/></div>" },
  "el-form": { template: "<form><slot/></form>" },
  "el-input": { template: "<input />" },
  "el-button": { template: "<button><slot/></button>" },
  "el-alert": { template: "<div class=\"alert\">审计日志查询失败</div>" },
  "el-empty": { template: "<div class=\"empty\">暂无审计日志</div>" },
  "el-table": { template: "<div class=\"table\"><slot/></div>" },
  "el-table-column": { template: "<div/>" },
  "el-pagination": { template: "<div/>" },
};

const global = { stubs, directives: { loading: () => undefined } };

describe("AuditLogPanel", () => {
  beforeEach(() => auditLogs.mockReset());

  it("renders empty state", async () => {
    auditLogs.mockResolvedValue({ data: { items: [], page: 1, page_size: 20, total: 0 } });
    const wrapper = mount(AuditLog, { global });
    await vi.waitFor(() => expect(auditLogs).toHaveBeenCalledTimes(1));
    await flushPromises();
    expect(wrapper.find(".empty").exists()).toBe(true);
    expect(wrapper.text()).toContain("暂无审计日志");
  });

  it("uses Chinese wording while keeping technical field identifiers", async () => {
    auditLogs.mockResolvedValue({ data: { items: [{ id: "a1", action: "agent.execute", status: "success", agent_id: "ag1", tool_id: "t1", created_at: "2026-08-29T10:00:00Z" }], page: 1, page_size: 20, total: 1 } });
    const wrapper = mount(AuditLog, { global });
    await vi.waitFor(() => expect(auditLogs).toHaveBeenCalledTimes(1));
    await flushPromises();
    expect(wrapper.text()).toContain("审计日志");
    expect(wrapper.text()).not.toContain("Audit Logs");
    expect(wrapper.text()).not.toContain("Status");
    expect(wrapper.text()).not.toContain("Created At");
  });

  it("renders error state", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);

    try {
      // 保持传输响应结构异常，验证组件错误分支，同时避免 Vitest 出现未处理拒绝。
      auditLogs.mockResolvedValue(undefined);

      const wrapper = mount(AuditLog, { global });
      await vi.waitFor(() => expect(auditLogs).toHaveBeenCalledTimes(1));
      await flushPromises();

      expect(wrapper.find(".alert").exists()).toBe(true);
      expect(wrapper.text()).toContain("审计日志查询失败");
      expect(consoleError).toHaveBeenCalledTimes(1);
    } finally {
      consoleError.mockRestore();
    }
  });
});
