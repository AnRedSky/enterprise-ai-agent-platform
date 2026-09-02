import { beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";

const mocks = vi.hoisted(() => ({
  executions: vi.fn(),
  execution: vi.fn(),
  executionEvents: vi.fn(),
  executionTrace: vi.fn(),
  auditLogs: vi.fn(),
  workflowExecution: vi.fn(),
  listExecutions: vi.fn(),
  triggers: vi.fn(),
  push: vi.fn(),
}));

vi.mock("../../src/api/runtime", () => ({ runtimeApi: {
  executions: mocks.executions,
  execution: mocks.execution,
  executionEvents: mocks.executionEvents,
  executionTrace: mocks.executionTrace,
  auditLogs: mocks.auditLogs,
} }));
vi.mock("../../src/api/workflows", () => ({ workflowApi: {
  execution: mocks.workflowExecution,
  listExecutions: mocks.listExecutions,
  triggers: mocks.triggers,
} }));
vi.mock("vue-router", () => ({
  useRoute: () => ({ query: { execution_id: "exec-deep-42", workflow_id: "workflow-7", source: "runtime-relation" } }),
  useRouter: () => ({ push: mocks.push }),
}));
vi.mock("element-plus", () => ({ ElMessage: { error: vi.fn(), success: vi.fn() }, ElMessageBox: { confirm: vi.fn() } }));

import Runtime from "../../src/views/runtime/components/RuntimeExecutions.vue";

const stubs = {
  "el-card": { template: "<div><slot name=\"header\"/><slot/></div>" },
  "el-form": { template: "<form><slot/></form>" },
  "el-input": { template: "<input />" },
  "el-button": { template: "<button><slot/></button>" },
  "el-alert": { props: ["title"], template: "<div>{{ title }}</div>" },
  "el-empty": { props: ["description"], template: "<div>{{ description }}</div>" },
  "el-pagination": { template: "<div />" },
  "el-drawer": { template: "<div><slot /></div>" },
  "el-descriptions": { template: "<div><slot /></div>" },
  "el-descriptions-item": { props: ["label"], template: "<div>{{ label }}<slot /></div>" },
  "el-timeline": { template: "<div><slot /></div>" },
  "el-timeline-item": { template: "<div><slot /></div>" },
  "el-divider": { template: "<div><slot /></div>" },
  "el-tag": { template: "<span><slot /></span>" },
  "el-date-picker": { template: "<input />" },
  "el-table": { template: "<div><slot /></div>" },
  "el-table-column": { template: "<div />" },
};

const global = { stubs, directives: { loading: () => undefined } };
const detail = { execution_id: "exec-deep-42", request_id: "request-1", trace_id: "trace-1", status: "failed", started_at: "2026-09-02", workflow_id: "workflow-7", workflow_version_id: "version-3" };
const workflowExecution = { id: "exec-deep-42", tenant_id: "tenant-1", workflow_id: "workflow-7", workflow_version_id: "version-3", status: "failed", created_at: "2026-09-02" };

beforeEach(() => {
  vi.clearAllMocks();
  mocks.executions.mockResolvedValue({ data: { items: [], page: 1, page_size: 20, total: 0 } });
  mocks.execution.mockResolvedValue({ data: { execution: detail, items: [] } });
  mocks.workflowExecution.mockResolvedValue({ data: workflowExecution });
  mocks.executionEvents.mockResolvedValue({ data: { items: [] } });
  mocks.executionTrace.mockResolvedValue({ data: { execution_id: "exec-deep-42", items: [] } });
  mocks.auditLogs.mockResolvedValue({ data: { items: [] } });
  mocks.listExecutions.mockResolvedValue({ data: [workflowExecution] });
  mocks.triggers.mockResolvedValue({ data: [] });
});

describe("Runtime durable deep-link recovery", () => {
  it("loads the exact execution_id even when it is absent from the paginated list", async () => {
    const wrapper = mount(Runtime, { global });
    await vi.waitFor(() => expect((wrapper.vm as any).loading).toBe(false));
    await vi.waitFor(() => expect(mocks.execution).toHaveBeenCalledWith("exec-deep-42"));
    expect((wrapper.vm as any).selected.execution_id).toBe("exec-deep-42");
    expect((wrapper.vm as any).selected.workflow_id).toBe("workflow-7");
  });

  it("keeps relation navigation on the backend execution id", async () => {
    const wrapper = mount(Runtime, { global });
    await vi.waitFor(() => expect((wrapper.vm as any).loading).toBe(false));
    await (wrapper.vm as any).navigateToExecution("parent-exec-9");
    expect(mocks.push).toHaveBeenCalledWith({
      path: "/runtime",
      query: { execution_id: "parent-exec-9", workflow_id: "workflow-7", source: "runtime-relation" },
    });
  });
});