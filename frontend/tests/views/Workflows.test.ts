import { beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";

const api = vi.hoisted(() => ({
  list: vi.fn(),
  create: vi.fn(),
  update: vi.fn(),
  versions: vi.fn(),
  createVersion: vi.fn(),
  publish: vi.fn(),
  createExecution: vi.fn(),
  runExecution: vi.fn(),
  execution: vi.fn(),
  executionNodes: vi.fn(),
  trace: vi.fn(),
  audit: vi.fn(),
}));

vi.mock("../../src/api/workflows", () => ({ workflowApi: api }));
vi.mock("element-plus", () => ({
  ElMessage: { error: vi.fn(), success: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn() },
}));

import Workflows from "../../src/views/workflows/index.vue";

const stubs = {
  "el-row": { template: "<div><slot /></div>" },
  "el-col": { template: "<div><slot /></div>" },
  "el-card": { template: "<div><slot name=\"header\"/><slot /></div>" },
  "el-form": { template: "<form><slot /></form>" },
  "el-form-item": { template: "<div><slot /></div>" },
  "el-input": { template: "<input />" },
  "el-button": { template: "<button><slot /></button>" },
  "el-divider": { template: "<hr />" },
  "el-table": { template: "<div class=\"table\"><slot /></div>" },
  "el-table-column": { template: "<div />" },
  "el-empty": { props: ["description"], template: "<div class=\"empty\">{{ description }}</div>" },
  "el-tag": { template: "<span><slot /></span>" },
  "el-descriptions": { template: "<div><slot /></div>" },
  "el-descriptions-item": { props: ["label"], template: "<div>{{ label }}: <slot /></div>" },
  "el-tabs": { template: "<div><slot /></div>" },
  "el-tab-pane": { template: "<div><slot /></div>" },
  "el-alert": { props: ["title"], template: "<div class=\"alert\">{{ title }}</div>" },
  "el-timeline": { template: "<div><slot /></div>" },
  "el-timeline-item": { template: "<div><slot /></div>" },
};

const global = { stubs, directives: { loading: () => undefined } };

const workflow = {
  id: "w1",
  name: "Order Workflow",
  description: "demo",
  owner_id: "u1",
  tenant_id: "t1",
  status: "published",
  published_version_id: "v1",
  created_at: "2026-08-20T00:00:00Z",
  updated_at: "2026-08-20T00:00:00Z",
};

describe("Workflow Governance view", () => {
  beforeEach(() => {
    Object.values(api).forEach((mock) => mock.mockReset());
    api.list.mockResolvedValue({ data: [] });
    api.versions.mockResolvedValue({ data: [] });
    api.audit.mockResolvedValue({ data: { items: [], page: 1, page_size: 50, total: 0 } });
    api.trace.mockResolvedValue({ data: { execution_id: "e1", items: [] } });
  });

  it("renders empty state when no workflows exist", async () => {
    const wrapper = mount(Workflows, { global });
    await vi.waitFor(() => expect(api.list).toHaveBeenCalled());
    expect(wrapper.text()).toContain("请选择 Workflow");
  });

  it("loads versions when a workflow is selected", async () => {
    api.list.mockResolvedValue({ data: [workflow] });
    api.versions.mockResolvedValue({ data: [{ id: "v1", workflow_id: "w1", version: 1, definition: { nodes: [] }, status: "published", created_by: "u1", created_at: "2026-08-20" }] });
    const wrapper = mount(Workflows, { global });
    await vi.waitFor(() => expect(api.list).toHaveBeenCalled());
    await (wrapper.vm as any).selectWorkflow(workflow);
    expect(api.versions).toHaveBeenCalledWith("w1");
    expect(wrapper.text()).toContain("Order Workflow");
  });

  it("creates and runs an execution for the selected published workflow", async () => {
    api.list.mockResolvedValue({ data: [workflow] });
    api.createExecution.mockResolvedValue({ data: { id: "e1", status: "pending", workflow_id: "w1", workflow_version_id: "v1", input_data: {}, created_at: "2026-08-20" } });
    api.runExecution.mockResolvedValue({ data: { id: "e1", status: "completed", workflow_id: "w1", workflow_version_id: "v1", input_data: {}, output_data: { ok: true }, created_at: "2026-08-20" } });
    api.executionNodes.mockResolvedValue({ data: [] });
    const wrapper = mount(Workflows, { global });
    await vi.waitFor(() => expect(api.list).toHaveBeenCalled());
    await (wrapper.vm as any).selectWorkflow(workflow);
    await (wrapper.vm as any).createExecution();
    expect(api.createExecution).toHaveBeenCalledWith("w1", {});
    await (wrapper.vm as any).runExecution();
    expect(api.runExecution).toHaveBeenCalledWith("e1");
    expect(api.executionNodes).toHaveBeenCalledWith("e1");
    expect((wrapper.vm as any).execution.status).toBe("completed");
  });

  it("loads execution status and node states from a real execution id", async () => {
    api.list.mockResolvedValue({ data: [workflow] });
    api.execution.mockResolvedValue({ data: { id: "e1", tenant_id: "t1", workflow_id: "w1", workflow_version_id: "v1", created_by: "u1", status: "completed", current_node_id: "output", input_data: {}, output_data: { ok: true }, created_at: "2026-08-20" } });
    api.executionNodes.mockResolvedValue({ data: [{ id: "n1", execution_id: "e1", node_id: "output", status: "completed", attempt: 1, created_at: "2026-08-20" }] });
    const wrapper = mount(Workflows, { global });
    await vi.waitFor(() => expect(api.list).toHaveBeenCalled());
    await (wrapper.vm as any).selectWorkflow(workflow);
    (wrapper.vm as any).executionId = "e1";
    await (wrapper.vm as any).loadExecution();
    expect(api.execution).toHaveBeenCalledWith("e1");
    expect(api.executionNodes).toHaveBeenCalledWith("e1");
    expect(wrapper.text()).toContain("completed");
    expect(wrapper.text()).toContain("output");
  });
});
