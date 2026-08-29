import { describe, expect, it, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";

const { executions, executionEvents, executionTrace } = vi.hoisted(() => ({ executions: vi.fn(), executionEvents: vi.fn(), executionTrace: vi.fn() }));
vi.mock("../../src/api/runtime", () => ({ runtimeApi: { executions, executionEvents, executionTrace } }));
vi.mock("element-plus", () => ({ ElMessage: { error: vi.fn(), success: vi.fn() } }));
import Runtime from "../../src/views/runtime/components/RuntimeExecutions.vue";

const stubs = {
  "el-card": { template: "<div><slot name=\"header\"/><slot/></div>" },
  "el-form": { template: "<form><slot/></form>" }, "el-input": { template: "<input />" },
  "el-button": { template: "<button @click=\"$emit('click')\"><slot/></button>" },
  "el-alert": { template: "<div class=\"alert\">运行记录查询失败，请稍后重试</div>" },
  "el-empty": { template: "<div class=\"empty\">empty</div>" }, "el-table": { template: "<div class=\"table\"><slot/></div>" },
  "el-table-column": { template: "<div><slot name=\"default\" :row=\"{}\"/></div>" }, "el-pagination": { template: "<div/>" }, "el-drawer": { template: "<div><slot/></div>" },
  "el-descriptions": { template: "<div><slot/></div>" }, "el-descriptions-item": { template: "<div><slot/></div>" },
  "el-timeline": { template: "<div><slot/></div>" }, "el-timeline-item": { template: "<div><slot/></div>" },
  "el-divider": { template: "<div><slot/></div>" }, "el-tag": { template: "<span><slot/></span>" },
};
const global = { stubs, directives: { loading: () => undefined } };

describe("RuntimeExecutions", () => {
  beforeEach(() => { executions.mockReset(); executionEvents.mockReset(); executionTrace.mockReset(); });
  it("renders Chinese empty state", async () => {
    executions.mockResolvedValue({ data: { items: [], page: 1, page_size: 20, total: 0 } });
    const wrapper = mount(Runtime, { global });
    await vi.waitFor(() => expect(executions).toHaveBeenCalled());
    expect(wrapper.text()).toContain("暂无运行记录");
    expect(wrapper.text()).not.toContain("Runtime Executions");
  });
  it("renders Chinese error state", async () => {
    executions.mockRejectedValue(new Error("network"));
    const wrapper = mount(Runtime, { global });
    await vi.waitFor(() => expect(wrapper.text()).toContain("运行记录查询失败，请稍后重试"));
  });
  it("maps runtime span and event identifiers to Chinese labels while preserving codes", async () => {
    executions.mockResolvedValue({ data: { items: [], page: 1, page_size: 20, total: 0 } });
    executionEvents.mockResolvedValue({ data: { execution: {}, items: [{ id: "event-1", span_type: "retrieval", status: "success", started_at: "2026-01-01", duration_ms: 10 }] } });
    executionTrace.mockResolvedValue({ data: { execution_id: "e1", items: [{ id: "trace-1", tenant_id: "tenant-1", execution_id: "e1", workflow_id: "w1", workflow_version_id: "v1", node_id: "input", event_type: "node_completed", status: "success", trace_id: "t1", created_at: "2026-01-01", error_code: "HTTP_ERROR", error_message: "upstream failure" }] } });
    const wrapper = mount(Runtime, { global });
    await vi.waitFor(() => expect(executions).toHaveBeenCalled());
    await (wrapper.vm as any).open({ execution_id: "e1", request_id: "r1", trace_id: "t1", session_id: "s1", agent_id: "a1", status: "success", started_at: "2026-01-01", duration_ms: 1200 });
    expect(wrapper.text()).toContain("检索（retrieval）");
    expect(wrapper.text()).toContain("节点完成（node_completed）");
    expect(wrapper.text()).toContain("外部请求失败（HTTP_ERROR）");
    expect(wrapper.text()).not.toContain("upstream failure");
  });
  it("normalizes backend success status to the completed presentation", async () => {
    executions.mockResolvedValue({ data: { items: [], page: 1, page_size: 20, total: 0 } });
    const wrapper = mount(Runtime, { global });
    await vi.waitFor(() => expect(executions).toHaveBeenCalled());
    expect((wrapper.vm as any).getRuntimeStatusMeta("success").label).toBe("已完成");
    expect((wrapper.vm as any).getRuntimeStatusMeta("succeeded").label).toBe("已完成");
  });
  it("keeps technical identifiers unchanged when copying", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { writeText } });
    executions.mockResolvedValue({ data: { items: [], page: 1, page_size: 20, total: 0 } });
    const wrapper = mount(Runtime, { global });
    await vi.waitFor(() => expect(executions).toHaveBeenCalled());
    await (wrapper.vm as any).copyRuntimeId("execution-123");
    expect(writeText).toHaveBeenCalledWith("execution-123");
  });
});
