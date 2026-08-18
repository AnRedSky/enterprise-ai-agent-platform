import { describe, expect, it, vi, beforeEach } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";

const { auditLogs } = vi.hoisted(() => ({ auditLogs: vi.fn() }));
vi.mock("../../src/api/runtime", () => ({ runtimeApi: { auditLogs } }));
vi.mock("element-plus", () => ({ ElMessage: { error: vi.fn() } }));

import AuditLog from "../../src/views/AuditLog.vue";

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
    await flushPromises();
    expect(auditLogs).toHaveBeenCalledTimes(1);
    expect(wrapper.find(".empty").exists()).toBe(true);
    expect(wrapper.text()).toContain("empty");
  });

  it("renders error state", async () => {
    auditLogs.mockResolvedValue({});
    const wrapper = mount(AuditLog, { global });
    await flushPromises();
    expect(auditLogs).toHaveBeenCalledTimes(1);
    expect(wrapper.find(".alert").exists()).toBe(true);
    expect(wrapper.text()).toContain("Audit 查询失败");
  });
});
