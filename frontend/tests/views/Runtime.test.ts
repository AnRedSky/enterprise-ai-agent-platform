import { describe, expect, it, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";

const { executions, execution, executionEvents, executionTrace, auditLogs, listExecutions, triggers, runExecution, cancelExecution, retryExecution, resumeExecution, push } = vi.hoisted(() => ({
  executions: vi.fn(), execution: vi.fn(), executionEvents: vi.fn(), executionTrace: vi.fn(), auditLogs: vi.fn(), listExecutions: vi.fn(), triggers: vi.fn(),
  runExecution: vi.fn(), cancelExecution: vi.fn(), retryExecution: vi.fn(), resumeExecution: vi.fn(), push: vi.fn(),
}));
vi.mock("../../src/api/runtime", () => ({ runtimeApi: { executions, execution, executionEvents, executionTrace, auditLogs } }));
vi.mock("../../src/api/workflows", () => ({ workflowApi: { execution, listExecutions, triggers, runExecution, cancelExecution, retryExecution, resumeExecution } }));
vi.mock("vue-router", () => ({ useRoute: () => ({ query: {} }), useRouter: () => ({ push }) }));
vi.mock("element-plus", () => ({ ElMessage: { error: vi.fn(), success: vi.fn() }, ElMessageBox: { confirm: vi.fn().mockResolvedValue(true) } }));
import Runtime from "../../src/views/runtime/components/RuntimeExecutions.vue";

const stubs = {
  "el-card": { template: "<div><slot name=\"header\"/><slot/></div>" }, "el-form": { template: "<form><slot/></form>" }, "el-input": { template: "<input />" },
  "el-button": { template: "<button @click=\"$emit('click')\"><slot/></button>" },
  "el-alert": { template: "<div class=\"alert\">{{ title }}</div>", props: ["title"] }, "el-empty": { template: "<div class=\"empty\">{{ description }}</div>", props: ["description"] },
  "el-table": { template: "<div class=\"table\"><slot/></div>" }, "el-table-column": { template: "<div><slot name=\"default\" :row=\"{}\"/></div>" },
  "el-pagination": { template: "<div/>" }, "el-drawer": { template: "<div><slot/></div>" }, "el-descriptions": { template: "<div><slot/></div>" }, "el-descriptions-item": { template: "<div><slot/></div>" },
  "el-timeline": { template: "<div><slot/></div>" }, "el-timeline-item": { template: "<div><slot/></div>" }, "el-divider": { template: "<div><slot/></div>" }, "el-tag": { template: "<span><slot/></span>" },
};
const global = { stubs, directives: { loading: () => undefined } };
const runtimeDetail = { execution_id: "e1", request_id: "r1", trace_id: "t1", status: "failed", started_at: "2026-01-01", workflow_id: "w1", workflow_version_id: "v1" };
const workflowDetail = { id: "e1", tenant_id: "t1", workflow_id: "w1", workflow_version_id: "v1", created_by: "u1", retry_of_execution_id: "parent-1", resume_of_execution_id: undefined, resume_checkpoint_sequence: undefined, status: "failed", input_data: {}, created_at: "2026-01-01" };
const triggerDetail = { id: "trigger-1", tenant_id: "t1", workflow_id: "w1", name: "生产调度", trigger_type: "scheduled", status: "enabled", config: {}, created_by: "u1", created_at: "2026-01-01", updated_at: "2026-01-01" };
const auditDetail = { id: "audit-1", actor_id: "u1", execution_id: "e1", action: "workflow.execution.retry", status: "success", created_at: "2026-01-01" };

beforeEach(() => {
  vi.clearAllMocks(); executions.mockResolvedValue({ data: { items: [], page: 1, page_size: 20, total: 0 } });
  execution.mockResolvedValue({ data: { execution: runtimeDetail, items: [] } }); executionEvents.mockResolvedValue({ data: { execution: runtimeDetail, items: [] } });
  executionTrace.mockResolvedValue({ data: { execution_id: "e1", items: [] } }); auditLogs.mockResolvedValue({ data: { items: [], page: 1, page_size: 50, total: 0 } });
  listExecutions.mockResolvedValue({ data: [workflowDetail] }); triggers.mockResolvedValue({ data: [] });
});

describe("RuntimeExecutions", () => {
  it("renders Chinese empty state", async () => { const wrapper = mount(Runtime, { global }); await vi.waitFor(() => expect(executions).toHaveBeenCalled()); expect(wrapper.text()).toContain("暂无运行记录"); });
  it("loads backend retry/resume relationship fields and derived executions", async () => {
    listExecutions.mockResolvedValue({ data: [workflowDetail, { ...workflowDetail, id: "retry-1", retry_of_execution_id: "e1" }, { ...workflowDetail, id: "resume-1", retry_of_execution_id: undefined, resume_of_execution_id: "e1", resume_checkpoint_sequence: 4 }] });
    const wrapper = mount(Runtime, { global }); await vi.waitFor(() => expect(executions).toHaveBeenCalled()); await (wrapper.vm as any).open({ execution_id: "e1" });
    expect(wrapper.text()).toContain("Retry 来源"); expect(wrapper.text()).toContain("parent-1"); expect(wrapper.text()).toContain("retry-1"); expect(wrapper.text()).toContain("resume-1"); expect(wrapper.text()).toContain("4");
    expect(listExecutions).toHaveBeenCalledWith("w1");
  });
  it("builds Trigger → Execution → Trace → Audit correlation from backend identifiers", async () => {
    triggers.mockResolvedValue({ data: [triggerDetail] }); auditLogs.mockResolvedValue({ data: { items: [auditDetail], page: 1, page_size: 50, total: 1 } });
    executionTrace.mockResolvedValue({ data: { execution_id: "e1", items: [{ id: "trace-1", tenant_id: "t1", execution_id: "e1", workflow_id: "w1", workflow_version_id: "v1", event_type: "execution_started", status: "running", trace_id: "t1", data: { trigger_id: "trigger-1" }, created_at: "2026-01-01" }] } });
    const wrapper = mount(Runtime, { global }); await vi.waitFor(() => expect(executions).toHaveBeenCalled()); await (wrapper.vm as any).open({ execution_id: "e1" });
    await vi.waitFor(() => expect(auditLogs).toHaveBeenCalledWith({ execution_id: "e1", page: 1, page_size: 50 }));
    expect(triggers).toHaveBeenCalledWith("w1"); expect(wrapper.text()).toContain("执行可观测关联"); expect(wrapper.text()).toContain("trigger-1"); expect(wrapper.text()).toContain("scheduled（Scheduler）"); expect(wrapper.text()).toContain("Audit 审计"); expect(wrapper.text()).toContain("workflow.execution.retry");
  });
  it("does not infer a Trigger when backend provides no Trigger identifier", async () => {
    triggers.mockResolvedValue({ data: [triggerDetail] });
    const wrapper = mount(Runtime, { global }); await vi.waitFor(() => expect(executions).toHaveBeenCalled()); await (wrapper.vm as any).open({ execution_id: "e1" });
    expect(wrapper.text()).toContain("未解析"); expect(wrapper.text()).toContain("Trigger ID");
  });
  it("navigates from a parent or child execution using its real id", async () => {
    const wrapper = mount(Runtime, { global }); await vi.waitFor(() => expect(executions).toHaveBeenCalled()); await (wrapper.vm as any).open({ execution_id: "e1" });
    await (wrapper.vm as any).navigateToExecution("parent-1");
    expect(push).toHaveBeenCalledWith({ path: "/runtime", query: { execution_id: "parent-1", workflow_id: "w1", source: "runtime-relation" } });
  });
  it("keeps retry and resume actions backed by workflow execution APIs", async () => {
    retryExecution.mockResolvedValue({ data: { id: "retry-2" } }); resumeExecution.mockResolvedValue({ data: { id: "resume-2" } });
    const wrapper = mount(Runtime, { global }); await vi.waitFor(() => expect(executions).toHaveBeenCalled()); await (wrapper.vm as any).open({ execution_id: "e1" });
    await (wrapper.vm as any).retrySelected(); expect(retryExecution).toHaveBeenCalledWith("e1"); await (wrapper.vm as any).resumeSelected(); expect(resumeExecution).toHaveBeenCalledWith("e1");
  });
  it("does not expose raw backend errors in relationship loading", async () => { listExecutions.mockRejectedValue(new Error("500 Internal Server Error")); const wrapper = mount(Runtime, { global }); await vi.waitFor(() => expect(executions).toHaveBeenCalled()); await (wrapper.vm as any).open({ execution_id: "e1" }); expect(wrapper.text()).not.toContain("500 Internal Server Error"); });
});
