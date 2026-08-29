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
  "el-table-column": { props: ["label"], template: "<div><span>{{ label }}</span><slot name=\"default\" :row=\"{ action: 'agent.execute', status: 'success' }\" /></div>" },
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
  it("maps audit action and status to Chinese while preserving technical codes", async () => {
    auditLogs.mockResolvedValue({ data: { items: [{ id: "a1", action: "agent.execute", status: "success", agent_id: "ag1", tool_id: "t1", created_at: "2026-08-29T10:00:00Z" }], page: 1, page_size: 20, total: 1 } });
    const wrapper = mount(AuditLog, { global });
    await vi.waitFor(() => expect(auditLogs).toHaveBeenCalledTimes(1));
    await flushPromises();
    expect((wrapper.vm as any).actionLabel("agent.execute")).toBe("智能体执行（agent.execute）");
    expect((wrapper.vm as any).statusLabel("success")).toBe("成功（success）");
    expect(wrapper.text()).not.toContain("Audit Logs");
    expect(wrapper.text()).not.toContain("Status");
    expect(wrapper.text()).not.toContain("Created At");
  });
  it("renders error state", async () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
    try {
      auditLogs.mockResolvedValue(undefined);
      const wrapper = mount(AuditLog, { global });
      await vi.waitFor(() => expect(auditLogs).toHaveBeenCalledTimes(1));
      await flushPromises();
      expect(wrapper.find(".alert").exists()).toBe(true);
      expect(wrapper.text()).toContain("审计日志查询失败");
      expect(consoleError).toHaveBeenCalledTimes(1);
    } finally { consoleError.mockRestore(); }
  });
});
