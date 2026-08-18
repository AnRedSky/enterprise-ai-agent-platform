import { describe, expect, it, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import Runtime from "./Runtime.vue";

const executions = vi.fn();
const executionEvents = vi.fn();
vi.mock("../api/runtime", () => ({
  runtimeApi: { executions, executionEvents },
}));
vi.mock("element-plus", async () => {
  const h = await import("vue");
  return {
    ElMessage: { error: vi.fn() },
    ElCard: { template: "<div><slot name=\"header\"/><slot/></div>" },
    ElForm: { template: "<form><slot/></form>" }, ElInput: { template: "<input />" }, ElButton: { template: "<button><slot/></button>" },
    ElAlert: { template: "<div class=\"alert\"><slot/></div>" }, ElEmpty: { template: "<div class=\"empty\">empty</div>" },
    ElTable: { template: "<div class=\"table\"><slot/></div>" }, ElTableColumn: { template: "<div/>" }, ElPagination: { template: "<div/>" },
    ElDrawer: { template: "<div><slot/></div>" }, ElDescriptions: { template: "<div><slot/></div>" }, ElDescriptionsItem: { template: "<div><slot/></div>" }, ElTimeline: { template: "<div><slot/></div>" }, ElTimelineItem: { template: "<div><slot/></div>" },
    vLoading: {},
  };
});

describe("Runtime.vue", () => {
  beforeEach(() => { executions.mockReset(); executionEvents.mockReset(); });

  it("renders empty state when execution list is empty", async () => {
    executions.mockResolvedValue({ data: { items: [], page: 1, page_size: 20, total: 0 } });
    const wrapper = mount(Runtime, { global: { stubs: { ElCard: true } } });
    await vi.waitFor(() => expect(executions).toHaveBeenCalled());
    expect(wrapper.text()).toContain("empty");
  });

  it("renders error state when execution query fails", async () => {
    executions.mockRejectedValue(new Error("network"));
    const wrapper = mount(Runtime);
    await vi.waitFor(() => expect(wrapper.text()).toContain("Runtime 查询失败，请稍后重试"));
  });

  it("loads execution events after opening a row", async () => {
    const item = { execution_id: "e1", request_id: "r1", trace_id: "t1", agent_id: "a1", status: "success", started_at: "2026-01-01" };
    executions.mockResolvedValue({ data: { items: [item], page: 1, page_size: 20, total: 1 } });
    executionEvents.mockResolvedValue({ data: { execution: item, items: [] } });
    const wrapper = mount(Runtime);
    await vi.waitFor(() => expect(executions).toHaveBeenCalled());
    await (wrapper.vm as any).open(item);
    expect(executionEvents).toHaveBeenCalledWith("e1");
  });
});
