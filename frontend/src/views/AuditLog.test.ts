import { describe, expect, it, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";

const { auditLogs } = vi.hoisted(() => ({ auditLogs: vi.fn() }));
vi.mock("../api/runtime", () => ({ runtimeApi: { auditLogs } }));
vi.mock("element-plus", () => ({ ElMessage: { error: vi.fn() } }));

import AuditLog from "./AuditLog.vue";

const stubs = {
  "el-card": { template: "<div><slot name=\"header\"/><slot/></div>" },
  "el-form": { template: "<form><slot/></form>" },
  "el-input": { template: "<input />" },
  "el-button": { template: "<button><slot/></button>" },
  "el-alert": { template: "<div class=\"alert\">Audit 查询失败</div>" },
  "el-empty": { template: "<div class=\"empty\">empty</div>" },
  "el-table": { template: "<div class=\"table\"><slot/></div>" },
  "el-table-column": { template: "<div/>" },
  "el-pagination": { template: "<div/>" },
};

const global = { stubs, directives: { loading: () => undefined } };

describe("AuditLog.vue", () => {
  beforeEach(() => auditLogs.mockReset());

  it("renders empty state", async () => {
    auditLogs.mockResolvedValue({ data: { items: [], page: 1, page_size: 20, total: 0 } });
    const wrapper = mount(AuditLog, { global });
    await vi.waitFor(() => expect(auditLogs).toHaveBeenCalled());
    expect(wrapper.text()).toContain("empty");
  });

  it("renders error state", async () => {
    auditLogs.mockRejectedValue(new Error("network"));
    const wrapper = mount(AuditLog, { global });
    await vi.waitFor(() => expect(wrapper.text()).toContain("Audit 查询失败"));
  });
});
