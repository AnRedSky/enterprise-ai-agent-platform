import { describe, expect, it, vi, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import WorkflowLifecycle from "@/views/workflows/WorkflowLifecycle.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import SurfaceCard from "@/components/ui/SurfaceCard.vue";
import StatePanel from "@/components/ui/StatePanel.vue";
import ConfirmDialog from "@/components/ui/ConfirmDialog.vue";
import { workflowApi } from "@/api/workflows";

const router = { push: vi.fn() };
const route = { query: {} as Record<string, string> };
vi.mock("vue-router", () => ({ useRouter: () => router, useRoute: () => route }));
vi.mock("@/api/workflows", () => ({ workflowApi: { list: vi.fn(), versions: vi.fn(), triggers: vi.fn(), listExecutions: vi.fn(), schedule: vi.fn(), invokeTrigger: vi.fn() } }));

const global = {
  stubs: {
    "el-card": { template: "<div><slot name='header'/><slot/></div>" },
    "el-select": { props: ["modelValue"], emits: ["update:modelValue"], template: "<div><slot/></div>" },
    "el-option": { template: "<option><slot/></option>" },
    "el-button": { props: ["loading", "disabled"], emits: ["click"], template: `<button :disabled="disabled" @click="$emit('click')"><slot/></button>` },
    "el-tag": { template: "<span><slot/></span>" },
    "el-empty": { props: ["description"], template: "<div>{{ description }}</div>" },
    "el-row": { template: "<div><slot/></div>" },
    "el-col": { template: "<div><slot/></div>" },
    "el-descriptions": { template: "<div><slot/></div>" },
    "el-descriptions-item": { props: ["label"], template: "<div>{{ label }}<slot/></div>" },
    "el-table": { template: "<div><slot/></div>" },
    "el-table-column": { template: "<span/>" },
    "el-alert": { props: ["title"], template: "<div>{{ title }}</div>" },
    "el-icon": { template: "<span><slot/></span>" },
    "el-dialog": { props: ["modelValue", "title"], template: "<div v-if=\"modelValue\"><strong>{{ title }}</strong><slot/><slot name='footer'/></div>" },
  },
  directives: { loading: () => undefined },
};

const workflow = { id: "w1", name: "订单审批", description: "", owner_id: "u1", tenant_id: "t1", status: "published", published_version_id: "v2", created_at: "2026-08-30T08:00:00Z", updated_at: "2026-08-30T08:10:00Z" };
const version = { id: "v2", workflow_id: "w1", version: 2, definition: {}, status: "published", created_by: "u1", created_at: "2026-08-30T08:05:00Z" };
const execution = { id: "e1", tenant_id: "t1", workflow_id: "w1", workflow_version_id: "v2", created_by: "u1", status: "completed", input_data: {}, created_at: "2026-08-30T08:00:00Z" };
const manualTrigger = { id: "t1", tenant_id: "t1", workflow_id: "w1", name: "人工执行", trigger_type: "manual", status: "enabled", config: {}, created_by: "u1", created_at: "2026-08-30T08:00:00Z", updated_at: "2026-08-30T08:00:00Z" };

beforeEach(() => {
  vi.clearAllMocks();
  route.query = {};
  vi.mocked(workflowApi.list).mockResolvedValue({ data: [workflow] } as never);
  vi.mocked(workflowApi.versions).mockResolvedValue({ data: [version] } as never);
  vi.mocked(workflowApi.triggers).mockResolvedValue({ data: [manualTrigger] } as never);
  vi.mocked(workflowApi.listExecutions).mockResolvedValue({ data: [execution] } as never);
  vi.mocked(workflowApi.invokeTrigger).mockResolvedValue({ data: { ...execution, id: "e2", status: "pending" } } as never);
});

describe("WorkflowLifecycle", () => {
  it("uses shared page header and surface card patterns", async () => {
    const wrapper = mount(WorkflowLifecycle, { global });
    await vi.waitFor(() => expect(wrapper.text()).toContain("订单审批"));
    expect(wrapper.findComponent(PageHeader).exists()).toBe(true);
    expect(wrapper.findAllComponents(SurfaceCard).length).toBeGreaterThanOrEqual(3);
  });

  it("uses the shared state panel for an ordinary list failure", async () => {
    vi.mocked(workflowApi.list).mockRejectedValueOnce(new Error("backend failure"));
    const wrapper = mount(WorkflowLifecycle, { global });
    await vi.waitFor(() => expect(wrapper.findComponent(StatePanel).props("state")).toBe("error"));
    expect(wrapper.findComponent(StatePanel).props("title")).toBe("工作流加载失败");
    expect(wrapper.text()).toContain("无法同步工作流数据，请检查服务状态后重试。");
  });

  it("uses the shared permission state for a forbidden list request", async () => {
    vi.mocked(workflowApi.list).mockRejectedValueOnce({ response: { status: 403 } });
    const wrapper = mount(WorkflowLifecycle, { global });
    await vi.waitFor(() => expect(wrapper.findComponent(StatePanel).props("state")).toBe("permission"));
    expect(wrapper.findComponent(StatePanel).props("title")).toBe("无权查看工作流");
    expect(wrapper.text()).toContain("当前账号没有工作流访问权限，请联系管理员。");
  });

  it("以真实 workflow/version/trigger/execution 数据构建生命周期工作台", async () => {
    const wrapper = mount(WorkflowLifecycle, { global });
    await vi.waitFor(() => expect(wrapper.text()).toContain("订单审批"));
    expect(wrapper.text()).toContain("当前生效版本");
    expect(wrapper.text()).toContain("触发与调度");
    expect(wrapper.text()).toContain("已完成");
  });

  it("从 Workflow 深链进入时按真实 workflow_id 恢复工作流上下文", async () => {
    route.query = { workflow_id: "w1", source: "runtime" };
    const wrapper = mount(WorkflowLifecycle, { global });
    await vi.waitFor(() => expect(wrapper.text()).toContain("订单审批"));
    expect((wrapper.vm as { selectedId: string }).selectedId).toBe("w1");
    expect(workflowApi.versions).toHaveBeenCalledWith("w1");
    expect(workflowApi.listExecutions).toHaveBeenCalledWith("w1");
  });

  it("从最近 Execution 进入 Runtime 时保留真实执行上下文", async () => {
    const wrapper = mount(WorkflowLifecycle, { global });
    await vi.waitFor(() => expect(wrapper.text()).toContain("进入 Runtime 诊断"));
    await (wrapper.vm as any).openRuntimeExecution(execution);
    expect(router.push).toHaveBeenCalledWith({ path: "/runtime", query: { tab: "executions", source: "workflow-lifecycle", execution_id: "e1", workflow_id: "w1", workflow_version_id: "v2" } });
  });

  it("无工作流时提供明确中文空状态", async () => {
    vi.mocked(workflowApi.list).mockResolvedValue({ data: [] } as never);
    const wrapper = mount(WorkflowLifecycle, { global });
    await vi.waitFor(() => expect(wrapper.text()).toContain("暂无工作流"));
    expect(wrapper.findComponent(StatePanel).props("state")).toBe("empty");
  });

  it("详情请求失败时显示共享错误状态并支持重新加载", async () => {
    vi.mocked(workflowApi.versions).mockRejectedValueOnce(new Error("detail failure"));
    const wrapper = mount(WorkflowLifecycle, { global });
    await vi.waitFor(() => expect(wrapper.findComponent(StatePanel).props("title")).toBe("工作流详情加载失败"));
    expect(wrapper.text()).toContain("无法同步当前工作流的版本、触发器或运行数据。");

    await (wrapper.vm as any).retryDetails();
    await vi.waitFor(() => expect(wrapper.findComponent(StatePanel).exists()).toBe(false));
    expect(workflowApi.versions).toHaveBeenCalledTimes(2);
    expect(workflowApi.triggers).toHaveBeenCalledTimes(2);
    expect(workflowApi.listExecutions).toHaveBeenCalledTimes(2);
  });

  it("手动触发器可确认并提交一次真实 Execution，然后刷新生命周期数据", async () => {
    const wrapper = mount(WorkflowLifecycle, { global });
    await vi.waitFor(() => expect(wrapper.text()).toContain("立即运行"));

    const action = wrapper.findAll("button").find((button) => button.text() === "立即运行");
    expect(action).toBeDefined();
    await action!.trigger("click");
    expect(wrapper.findComponent(ConfirmDialog).exists()).toBe(true);
    expect(wrapper.text()).toContain("本次使用空输入数据，是否继续？");

    await (wrapper.vm as any).confirmInvoke();
    expect(workflowApi.invokeTrigger).toHaveBeenCalledWith("w1", "t1", {});
    await vi.waitFor(() => expect(workflowApi.listExecutions).toHaveBeenCalledTimes(2));
  });
});
