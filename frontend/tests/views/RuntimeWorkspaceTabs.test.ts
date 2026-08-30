import { beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";

const route = { query: {} as Record<string, string> };
const replace = vi.fn();

vi.mock("vue-router", () => ({ useRoute: () => route, useRouter: () => ({ replace }) }));
vi.mock("@/views/runtime/components/RuntimeExecutions.vue", () => ({ default: { template: "<div>runtime executions</div>" } }));
vi.mock("@/views/runtime/components/RuntimeObservabilityOverview.vue", () => ({ default: { template: "<div>runtime overview</div>" } }));

import RuntimeWorkspaceTabs from "@/views/runtime/components/RuntimeWorkspaceTabs.vue";

const global = {
  stubs: {
    "el-tabs": { props: ["modelValue"], template: "<div><slot /></div>" },
    "el-tab-pane": { template: "<div><slot /></div>" },
    "el-tag": { template: "<span><slot /></span>" },
    "el-skeleton": { template: "<div />" },
    "el-alert": { template: "<div><slot /></div>" },
    "el-button": { template: `<button @click="$emit('click')"><slot/></button>` },
  },
};

beforeEach(() => { route.query = {}; replace.mockReset(); });

describe("RuntimeWorkspaceTabs", () => {
  it("opens Execution tab for agent debug deep links", () => {
    route.query = { source: "agent-debug", agent_id: "agent-1" };
    const wrapper = mount(RuntimeWorkspaceTabs, { global });
    expect((wrapper.vm as { activeTab: string }).activeTab).toBe("executions");
    expect((wrapper.vm as { executionsMounted: boolean }).executionsMounted).toBe(true);
  });
  it("opens Execution tab for workflow and trace context deep links", () => {
    route.query = { workflow_id: "workflow-1", trace_id: "trace-1" };
    const wrapper = mount(RuntimeWorkspaceTabs, { global });
    expect((wrapper.vm as { activeTab: string }).activeTab).toBe("executions");
  });
  it("returns to Workflow lifecycle with the real workflow context", () => {
    route.query = { workflow_id: "workflow-1", execution_id: "execution-1", source: "workflow-lifecycle" };
    const wrapper = mount(RuntimeWorkspaceTabs, { global });
    (wrapper.vm as { openWorkflowLifecycle: () => void }).openWorkflowLifecycle();
    expect(replace).toHaveBeenCalledWith({ path: "/workflows/lifecycle", query: { workflow_id: "workflow-1", source: "runtime" } });
  });
  it("does not create a Workflow lifecycle link without workflow context", () => {
    const wrapper = mount(RuntimeWorkspaceTabs, { global });
    (wrapper.vm as { openWorkflowLifecycle: () => void }).openWorkflowLifecycle();
    expect(replace).not.toHaveBeenCalled();
  });
  it("restores a valid tab from a deep link", () => {
    route.query = { tab: "diagnostics", execution_id: "execution-1", trace_id: "trace-1" };
    const wrapper = mount(RuntimeWorkspaceTabs, { global });
    expect((wrapper.vm as { activeTab: string }).activeTab).toBe("diagnostics");
    expect((wrapper.vm as { contextItems: Array<{ key: string; value: string }> }).contextItems).toEqual([
      { key: "execution_id", value: "execution-1" }, { key: "trace_id", value: "trace-1" },
    ]);
  });
  it("keeps overview as the default when no runtime context is supplied", () => {
    const wrapper = mount(RuntimeWorkspaceTabs, { global });
    expect((wrapper.vm as { activeTab: string }).activeTab).toBe("overview");
    expect((wrapper.vm as { executionsMounted: boolean }).executionsMounted).toBe(false);
  });
  it("persists the selected tab without dropping runtime context", () => {
    route.query = { source: "agent-debug", agent_id: "agent-1" };
    const wrapper = mount(RuntimeWorkspaceTabs, { global });
    (wrapper.vm as { selectTab: (tab: string) => void }).selectTab("diagnostics");
    expect(replace).toHaveBeenCalledWith({ path: "/runtime", query: { source: "agent-debug", agent_id: "agent-1", tab: "diagnostics" } });
  });
});