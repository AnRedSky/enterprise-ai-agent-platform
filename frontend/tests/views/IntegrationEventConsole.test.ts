import { describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { ElAlert, ElButton, ElDescriptions, ElDescriptionsItem, ElDivider, ElDrawer, ElEmpty, ElForm, ElInput, ElOption, ElPagination, ElSelect, ElTable, ElTableColumn, ElTag } from "element-plus";
import IntegrationEventConsole from "@/views/integrations/IntegrationEventConsole.vue";
import { integrationApi } from "@/api/integrations";

vi.mock("@/api/integrations", () => ({ integrationApi: { integrationEvents: vi.fn() } }));
const components = { ElAlert, ElButton, ElDescriptions, ElDescriptionsItem, ElDivider, ElDrawer, ElEmpty, ElForm, ElInput, ElOption, ElPagination, ElSelect, ElTable, ElTableColumn, ElTag };
function mountConsole() { return mount(IntegrationEventConsole, { global: { components, directives: { loading: () => undefined } } }); }
const event = {
  id: "e1", tenant_id: "t1", event_type: "workflow.execution.completed", schema_version: 1, source: "workflow", subject: "execution:ex1", idempotency_key: "workflow:ex1:completed", occurred_at: "2026-08-29T08:00:00Z", request_id: "req1", trace_id: "trace1", payload: { execution_id: "ex1", status: "completed" }, metadata_json: {}, status: "delivered", attempt_count: 1, next_attempt_at: null, last_attempt_at: "2026-08-29T08:00:01Z", delivered_at: "2026-08-29T08:00:01Z", last_error_code: null, created_at: "2026-08-29T08:00:00Z",
};

describe("IntegrationEventConsole", () => {
  it("展示事件事实并按查询条件请求", async () => {
    vi.mocked(integrationApi.integrationEvents).mockResolvedValue({ data: { items: [event], page: 1, page_size: 20, total: 1 } } as never);
    const wrapper = mountConsole();
    await vi.waitFor(() => expect(wrapper.text()).toContain("workflow.execution.completed"));
    expect(wrapper.text()).toContain("已送达");
    expect(integrationApi.integrationEvents).toHaveBeenCalledWith({ page: 1, page_size: 20 });
    const inputs = wrapper.findAll("input");
    await inputs[0].setValue("scheduler.dispatched");
    const queryButton = wrapper.findAll("button").find((button) => button.text() === "查询");
    await queryButton!.trigger("click");
    await vi.waitFor(() => expect(integrationApi.integrationEvents).toHaveBeenLastCalledWith({ page: 1, page_size: 20, event_type: "scheduler.dispatched" }));
  });

  it("点击事件打开详情并展示 payload", async () => {
    vi.mocked(integrationApi.integrationEvents).mockResolvedValue({ data: { items: [event], page: 1, page_size: 20, total: 1 } } as never);
    const wrapper = mountConsole();
    await vi.waitFor(() => expect(wrapper.text()).toContain("execution:ex1"));
    const row = wrapper.find("tbody tr");
    await row.trigger("click");
    await vi.waitFor(() => expect(wrapper.text()).toContain('"execution_id": "ex1"'));
    expect(wrapper.text()).toContain("幂等标识");
    expect(wrapper.text()).toContain("trace1");
  });
});
