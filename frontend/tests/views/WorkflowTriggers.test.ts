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

const messages = vi.hoisted(() => ({
  error: vi.fn(),
  success: vi.fn(),
  warning: vi.fn(),
}));

vi.mock("../../src/api/workflows", () => ({ workflowApi: api }));
vi.mock("element-plus", () => ({
  ElMessage: messages,
  ElMessageBox: { confirm: vi.fn() },
}));

import WorkflowTriggers from "../../src/views/workflow-triggers/index.vue";

const stubs = {
  "el-card": { template: "<div><slot name=\"header\"/><slot /></div>" },
  "el-button": { template: "<button @click=\"$emit('click')\"><slot /></button>" },
  "el-alert": { props: ["title"], template: "<div>{{ title }}</div>" },
  "el-form": { template: "<form><slot /></form>" },
  "el-form-item": { props: ["label"], template: "<div><div v-if=\"label\">{{ label }}</div><slot /></div>" },
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
  id: "w1", name: "Order Workflow", description: "demo", owner_id: "u1", tenant_id: "t1",
  status: "published", published_version_id: "v1", created_at: "2026-08-20T00:00:00Z", updated_at: "2026-08-20T00:00:00Z",
};

const manualTrigger = {
  id: "t1", tenant_id: "t1", workflow_id: "w1", name: "Manual Order Trigger", trigger_type: "manual" as const,
  status: "enabled" as const, config: {}, created_by: "u1", created_at: "2026-08-20T00:00:00Z", updated_at: "2026-08-20T00:00:00Z",
};

const scheduledTrigger = {
  id: "t2", tenant_id: "t1", workflow_id: "w1", name: "Scheduled Order Trigger", trigger_type: "scheduled" as const,
  status: "enabled" as const, config: { timezone: "Asia/Seoul", interval_seconds: 60 }, created_by: "u1",
  created_at: "2026-08-20T00:00:00Z", updated_at: "2026-08-20T00:00:00Z",
};

const global = { stubs, directives: { loading: () => undefined } };

describe("Workflow Trigger Governance view", () => {
  beforeEach(() => {
    Object.values(api).forEach((mock) => mock.mockReset());
    Object.values(messages).forEach((mock) => mock.mockReset());
    api.list.mockResolvedValue({ data: [workflow] });
    api.triggers.mockResolvedValue({ data: [manualTrigger, scheduledTrigger] });
    api.createTrigger.mockResolvedValue({ data: manualTrigger });
    api.updateTrigger.mockResolvedValue({ data: { ...manualTrigger, status: "disabled" } });
    api.deleteTrigger.mockResolvedValue({ data: undefined });
    api.invokeTrigger.mockResolvedValue({ data: { id: "e1", status: "completed", workflow_id: "w1", workflow_version_id: "v1", input_data: {}, created_at: "2026-08-20" } });
  });

  it("loads workflow trigger inventory", async () => {
    const wrapper = mount(WorkflowTriggers, { global });
    await vi.waitFor(() => expect(api.triggers).toHaveBeenCalledWith("w1"));
    expect(wrapper.text()).toContain("Workflow Trigger Governance");
    expect(wrapper.text()).toContain("Asia/Seoul / 每 60 秒");
  });

  it("renders schedule governance guidance without inventing scheduler state", async () => {
    const wrapper = mount(WorkflowTriggers, { global });
    await vi.waitFor(() => expect(api.triggers).toHaveBeenCalledWith("w1"));
    const text = wrapper.text();
    expect(text).toContain("timezone + interval_seconds Contract");
    expect(text).toContain("Scheduled Order Trigger");
    expect(text).toContain("Asia/Seoul / 每 60 秒");
    expect(text).not.toContain("next run");
  });

  it("creates a scheduled trigger with the backend schedule contract", async () => {
    const wrapper = mount(WorkflowTriggers, { global });
    await vi.waitFor(() => expect(api.triggers).toHaveBeenCalledWith("w1"));
    const vm = wrapper.vm as any;
    vm.form.name = "Hourly Order Trigger";
    vm.form.triggerType = "scheduled";
    vm.form.configText = JSON.stringify({ timezone: "UTC", interval_seconds: 3600 });
    await vm.createTrigger();
    expect(api.createTrigger).toHaveBeenCalledWith("w1", {
      name: "Hourly Order Trigger",
      trigger_type: "scheduled",
      config: { timezone: "UTC", interval_seconds: 3600 },
    });
  });

  it("rejects invalid scheduled configuration before issuing an HTTP request", async () => {
    const wrapper = mount(WorkflowTriggers, { global });
    await vi.waitFor(() => expect(api.triggers).toHaveBeenCalledWith("w1"));
    const vm = wrapper.vm as any;
    vm.form.name = "Invalid Schedule";
    vm.form.triggerType = "scheduled";
    vm.form.configText = JSON.stringify({ timezone: "UTC", interval_seconds: 0 });
    await vm.createTrigger();
    expect(api.createTrigger).not.toHaveBeenCalled();
    expect(messages.error).toHaveBeenCalledWith("Schedule interval_seconds 必须是大于 0 的整数");
  });

  it("creates, toggles and deletes a trigger through the frontend contract", async () => {
    const wrapper = mount(WorkflowTriggers, { global });
    await vi.waitFor(() => expect(api.triggers).toHaveBeenCalledWith("w1"));
    const vm = wrapper.vm as any;
    vm.form.name = "Manual Trigger 2";
    await vm.createTrigger();
    expect(api.createTrigger).toHaveBeenCalledWith("w1", { name: "Manual Trigger 2", trigger_type: "manual", config: {} });
    await vm.toggleTrigger(manualTrigger);
    expect(api.updateTrigger).toHaveBeenCalledWith("w1", "t1", { status: "disabled" });
    await vm.deleteTrigger(manualTrigger);
    expect(api.deleteTrigger).toHaveBeenCalledWith("w1", "t1");
  });

  it("rejects invalid Trigger Config before issuing an HTTP request", async () => {
    const wrapper = mount(WorkflowTriggers, { global });
    await vi.waitFor(() => expect(api.triggers).toHaveBeenCalledWith("w1"));
    const vm = wrapper.vm as any;
    vm.form.name = "Invalid Config Trigger";
    vm.form.configText = "{invalid-json";
    await vm.createTrigger();
    expect(api.createTrigger).not.toHaveBeenCalled();
    expect(messages.error).toHaveBeenCalledWith("Trigger Config 不是合法 JSON");
  });

  it("invokes an enabled manual trigger and exposes the resulting execution", async () => {
    const wrapper = mount(WorkflowTriggers, { global });
    await vi.waitFor(() => expect(api.triggers).toHaveBeenCalledWith("w1"));
    await (wrapper.vm as any).invokeTrigger(manualTrigger);
    expect(api.invokeTrigger).toHaveBeenCalledWith("w1", "t1", {}, expect.any(String));
    expect((wrapper.vm as any).execution.id).toBe("e1");
    expect(wrapper.text()).toContain("e1");
  });
});
