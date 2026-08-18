import { describe, expect, it, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import AuditLog from "./AuditLog.vue";

const auditLogs = vi.fn();
vi.mock("../api/runtime", () => ({ runtimeApi: { auditLogs } }));
vi.mock("element-plus", () => ({
  ElMessage: { error: vi.fn() },
  ElCard: { template: "<div><slot name=\"header\"/><slot/></div>" }, ElForm: { template: "<form><slot/></form>" }, ElInput: { template: "<input />" }, ElButton: { template: "<button><slot/></button>" },
  ElAlert: { template: "<div class=\"alert\">alert</div>" }, ElEmpty: { template: "<div class=\"empty\">empty</div>" }, ElTable: { template: "<div class=\"table\"><slot/></div>" }, ElTableColumn: { template: "<div/>" }, ElPagination: { template: "<div/>" },
}));

describe("AuditLog.vue", () => {
  beforeEach(() => auditLogs.mockReset());

  it("renders empty state", async () => {
    auditLogs.mockResolvedValue({ data: { items: [], page: 1, page_size: 20, total: 0 } });
    const wrapper = mount(AuditLog);
    await vi.waitFor(() => expect(auditLogs).toHaveBeenCalled());
    expect(wrapper.text()).toContain("empty");
  });

  it("renders error state", async () => {
    auditLogs.mockRejectedValue(new Error("network"));
    const wrapper = mount(AuditLog);
    await vi.waitFor(() => expect(wrapper.text()).toContain("Audit 查询失败"));
  });
});
