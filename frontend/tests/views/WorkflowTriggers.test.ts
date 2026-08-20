import { beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";

const api = vi.hoisted(() => ({
  list: vi.fn(),
  triggers: vi.fn(),
  createTrigger: vi.fn(),
  updateTrigger: vi.fn(),
  deleteTrigger: vi.fn(),
  invokeTrigger: vi.fn(),
}));

vi.mock("../../src/api/workflows", () => ({ workflowApi: api }));
vi.mock("element-plus", () => ({
  ElMessage: { error: vi.fn(), success: vi.fn(), warning: vi.fn() },
  ElMessageBox: { confirm: vi.fn() },
}));

import WorkflowTriggers from "../../src/views/workflow-triggers/index.vue";

const stubs = {
  "el-card": { template: "<div><slot name=\"header\"/><slot /></div>" },
  "el-button": { template: "<button @click=\"$emit('click')\"><slot /></button>" },
  "el-alert": { props: ["title"], template: "<div>{{ title }}</div>" },
  "el-form": { template: "<form><slot /></form>" },
  "el-form-item": { template: "<div><slot /></div>" },
  "el-select": { template: "<select><slot /></select>" },
  "el-option": { template: "<option><slot /></option>" },
  "el-input": { template: "<input />" },
  "el-tag": { template: "<span><slot /></span>" },
  "el-divider": { template: "<hr />" },
  "el-table": { template: "<div><slot /></div>" },
  "el-table-column": { template: "<div />" },
  "el-descriptions": { template: "<div><slot /></div>" },
  "el-descriptions-item": { props: ["label"], template: "<div>{{ label }}: <slot /></div>" },
};

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

const trigger = {
  id: "t1",
  tenant_id: "t1",
  workflow_id: "w1",
  name: "Manual Order Trigger",
  trigger_type: "manual" as const,
  status: "enabled" as const,
  config: {},
  created_by: "u1",
  created_at: "2026-08-20T00:00:00Z",
  updated_at: "2026-08-20T00:00:00Z",
};

const global = { stubs, directives: { loading: () => undefined } };

describe("Workflow Trigger Governance view", () => {
  beforeEach(() => {
    Object.values(api).forEach((mock) => mock.mockReset());
    api.list.mockResolvedValue({ data: [workflow] });
    api.triggers.mockResolvedValue({ data: [trigger] });
    api.createTrigger.mockResolvedValue({ data: trigger });
    api.updateTrigger.mockResolvedValue({ data: { ...trigger, status: "disabled" } });
    api.deleteTrigger.mockResolvedValue({ data: undefined });
    api.invokeTrigger.mockResolvedValue({ data: { id: "e1", status: "completed", workflow_id: "w1", workflow_version_id: "v1", input_data: {}, created_at: "2026-08-20" } });
  });

  it("loads workflow trigger inventory", async () => {
    const wrapper = mount(WorkflowTriggers, { global });
    await vi.waitFor(() => expect(api.triggers).toHaveBeenCalledWith("w1"));
    expect(wrapper.text()).toContain("Workflow Trigger Governance");
  });

  it("creates, toggles and deletes a trigger through the frontend contract", async () => {
    const wrapper = mount(WorkflowTriggers, { global });
    await vi.waitFor(() => expect(api.triggers).toHaveBeenCalledWith("w1"));
    (wrapper.vm as any).form.name = "Manual Trigger 2";
    await (wrapper.vm as any).createTrigger();
    expect(api.createTrigger).toHaveBeenCalledWith("w1", { name: "Manual Trigger 2", trigger_type: "manual", config: {} });
    await (wrapper.vm as any).toggleTrigger(trigger);
    expect(api.updateTrigger).toHaveBeenCalledWith("w1", "t1", { status: "disabled" });
    await (wrapper.vm as any).deleteTrigger(trigger);
    expect(api.deleteTrigger).toHaveBeenCalledWith("w1", "t1");
  });

  it("invokes an enabled trigger and exposes the resulting execution", async () => {
    const wrapper = mount(WorkflowTriggers, { global });
    await vi.waitFor(() => expect(api.triggers).toHaveBeenCalledWith("w1"));
    await (wrapper.vm as any).invokeTrigger(trigger);
    expect(api.invokeTrigger).toHaveBeenCalledWith("w1", "t1", {}, expect.any(String));
    expect((wrapper.vm as any).execution.id).toBe("e1");
    expect(wrapper.text()).toContain("e1");
  });
});
