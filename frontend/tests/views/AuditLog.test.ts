import { describe, expect, it, vi, beforeEach } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";

const { auditLogs, push } = vi.hoisted(() => ({ auditLogs: vi.fn(), push: vi.fn() }));
vi.mock("../../src/api/runtime", () => ({ runtimeApi: { auditLogs } }));
vi.mock("vue-router", () => ({ useRouter: () => ({ push }) }));

import AuditLog from "../../src/views/audit-log/components/AuditLogPanel.vue";

const stubs = {
  "el-card": { template: "<div><slot name=\"header\"/><slot/></div>" },
  "el-form": { template: "<form><slot/></form>" },
  "el-form-item": { template: "<label><slot/></label>" },
  "el-input": { template: "<input />" },
  "el-select": { template: "<select><slot/></select>" },
  "el-option": { props: ["label", "value"], template: "<option :value=\"value\">{{ label }}</option>" },
  "el-button": { template: "<button @click=\"$emit('click')\"><slot/></button>" },
  "el-alert": { template: "<div class=\"alert\"><slot/><span>{{ title }}</span></div>", props: ["title"] },
  "el-empty": { template: "<div class=\"empty\"><span>{{ description }}</span><slot/></div>", props: ["description"] },
  "el-table": { template: "<div class=\"table\"><slot/></div>" },
  "el-table-column": { props: ["label"], template: "<div><span>{{ label }}</span><slot name=\"default\" :row=\"{ action: 'agent.execute', status: 'success', execution_id: 'ex-12345678901234567890' }\" /></div>" },
  "el-tag": { template: "<span><slot/></span>" },
  "el-pagination": { template: "<div/>" },
};
const global = { stubs, directives: { loading: () => undefined } };

describe("AuditLogPanel", () => {
  beforeEach(() => { auditLogs.mockReset(); push.mockReset(); });

  it("renders empty state with a recovery action", async () => {
    auditLogs.mockResolvedValue({ data: { items: [], page: 1, page_size: 20, total: 0 } });
    const wrapper = mount(AuditLog, { global });
    await vi.waitFor(() => expect(auditLogs).toHaveBeenCalledTimes(1));
    await flushPromises();
    expect(wrapper.find(".empty").exists()).toBe(true);
    expect(wrapper.text()).toContain("暂无符合条件的审计日志");
  });

  it("maps audit action and status to Chinese while preserving technical codes", async () => {
    auditLogs.mockResolvedValue({ data: { items: [{ id: "a1", action: "agent.execute", status: "success", agent_id: "ag1", tool_id: "t1", execution_id: "ex1", created_at: "2026-08-29T10:00:00Z" }], page: 1, page_size: 20, total: 1 } });
    const wrapper = mount(AuditLog, { global });
    await vi.waitFor(() => expect(auditLogs).toHaveBeenCalledTimes(1));
    await flushPromises();
    expect((wrapper.vm as any).actionLabel("agent.execute")).toBe("智能体执行（agent.execute）");
    expect((wrapper.vm as any).statusLabel("success")).toBe("成功（success）");
    expect((wrapper.vm as any).statusType("failed")).toBe("danger");
    expect(wrapper.text()).not.toContain("Audit Logs");
    expect(wrapper.text()).not.toContain("Created At");
  });

  it("opens Runtime with the real execution context", async () => {
    auditLogs.mockResolvedValue({ data: { items: [{ id: "a1", action: "agent.execute", status: "success", execution_id: "ex-real", created_at: "2026-08-29T10:00:00Z" }], page: 1, page_size: 20, total: 1 } });
    const wrapper = mount(AuditLog, { global });
    await vi.waitFor(() => expect(auditLogs).toHaveBeenCalledTimes(1));
    await flushPromises();
    await (wrapper.vm as any).openExecution("ex-real");
    expect(push).toHaveBeenCalledWith({ path: "/runtime", query: { execution_id: "ex-real", source: "audit" } });
  });

  it("renders an actionable error state without exposing raw backend errors", async () => {
    auditLogs.mockRejectedValue(new Error("internal backend exception"));
    const wrapper = mount(AuditLog, { global });
    await vi.waitFor(() => expect(auditLogs).toHaveBeenCalledTimes(1));
    await flushPromises();
    expect(wrapper.find(".alert").exists()).toBe(true);
    expect(wrapper.text()).toContain("审计日志暂时无法加载");
    expect(wrapper.text()).not.toContain("internal backend exception");
  });
});
