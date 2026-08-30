import { describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import WorkflowLifecycle from "@/views/workflows/WorkflowLifecycle.vue";
import { workflowApi } from "@/api/workflows";

vi.mock("@/api/workflows", () => ({
  workflowApi: {
    list: vi.fn(),
    versions: vi.fn(),
    triggers: vi.fn(),
    listExecutions: vi.fn(),
    schedule: vi.fn(),
  },
}));

const global = {
  stubs: {
    "el-card": { template: "<div><slot name='header'/><slot/></div>" },
    "el-select": { props: ["modelValue"], emits: ["update:modelValue"], template: "<div><slot/></div>" },
    "el-option": { template: "<option><slot/></option>" },
    "el-button": { template: "<button><slot/></button>" },
    "el-tag": { template: "<span><slot/></span>" },
    "el-empty": { props: ["description"], template: "<div>{{ description }}</div>" },
    "el-row": { template: "<div><slot/></div>" },
    "el-col": { template: "<div><slot/></div>" },
    "el-descriptions": { template: "<div><slot/></div>" },
    "el-descriptions-item": { props: ["label"], template: "<div>{{ label }}<slot/></div>" },
    "el-table": { template: "<div><slot/></div>" },
    "el-table-column": { template: "<span/>" },
    "el-alert": { props: ["title"], template: "<div>{{ title }}</div>" },
  },
};

describe("WorkflowLifecycle", () => {
  it("以真实 workflow/version/trigger/execution 数据构建生命周期工作台", async () => {
    vi.mocked(workflowApi.list).mockResolvedValue({ data: [{ id: "w1", name: "订单审批", description: "", owner_id: "u1", tenant_id: "t1", status: "published", published_version_id: "v2", created_at: "2026-08-30T08:00:00Z", updated_at: "2026-08-30T08:10:00Z" }] } as never);
    vi.mocked(workflowApi.versions).mockResolvedValue({ data: [{ id: "v2", workflow_id: "w1", version: 2, definition: {}, status: "published", created_by: "u1", created_at: "2026-08-30T08:05:00Z" }] } as never);
    vi.mocked(workflowApi.triggers).mockResolvedValue({ data: [{ id: "tr1", tenant_id: "t1", workflow_id: "w1", name: "每小时调度", trigger_type: "scheduled", status: "enabled", config: { timezone: "Asia/Seoul", interval_seconds: 3600 }, created_by: "u1", created_at: "2026-08-30T08:00:00Z", updated_at: "2026-08-30T08:00:00Z" }] } as never);
    vi.mocked(workflowApi.schedule).mockResolvedValue({ data: { id: "s1", trigger_id: "tr1", workflow_id: "w1", tenant_id: "t1", enabled: true, status: "scheduled", timezone: "Asia/Seoul", next_run_at: "2026-08-30T09:00:00Z", last_run_at: "2026-08-30T08:00:00Z", last_execution_id: "e1", lease_active: false, misfire_policy: "skip", catch_up_limit: 1, updated_at: "2026-08-30T08:00:00Z" } } as never);
    vi.mocked(workflowApi.listExecutions).mockResolvedValue({ data: [{ id: "e1", tenant_id: "t1", workflow_id: "w1", workflow_version_id: "v2", created_by: "u1", status: "completed", input_data: {}, created_at: "2026-08-30T08:00:00Z" }] } as never);

    const wrapper = mount(WorkflowLifecycle, { global });
    await vi.waitFor(() => expect(wrapper.text()).toContain("订单审批"));
    expect(wrapper.text()).toContain("当前生效版本");
    expect(wrapper.text()).toContain("触发与调度");
    expect(wrapper.text()).toContain("每小时调度");
    expect(wrapper.text()).toContain("已完成");
    expect(workflowApi.schedule).toHaveBeenCalledWith("w1", "tr1");
  });

  it("无工作流时提供明确中文空状态", async () => {
    vi.mocked(workflowApi.list).mockResolvedValue({ data: [] } as never);
    const wrapper = mount(WorkflowLifecycle, { global });
    await vi.waitFor(() => expect(wrapper.text()).toContain("暂无工作流，请先创建工作流。"));
  });
});
