import { describe, expect, it, vi } from "vitest";
import { shallowMount } from "@vue/test-utils";
import Dashboard from "@/views/dashboard/components/DashboardOverview.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import MetricCard from "@/components/ui/MetricCard.vue";
import SurfaceCard from "@/components/ui/SurfaceCard.vue";

vi.mock("@/api/agents", () => ({ listAgents: vi.fn().mockResolvedValue([]) }));
vi.mock("@/api/tools", () => ({ listTools: vi.fn().mockResolvedValue([]) }));
vi.mock("@/api/runtime", () => ({ runtimeApi: { executions: vi.fn().mockResolvedValue({ data: { total: 0, items: [] } }) } }));
vi.mock("element-plus", () => ({ ElMessage: { error: vi.fn() } }));

const sharedStubs = {
  PageHeader: { props: ["title", "eyebrow", "description"], template: "<header><h1>{{ title }}</h1><slot name=\"actions\"/></header>" },
  SurfaceCard: { props: ["title", "description"], template: "<section><h2>{{ title }}</h2><slot/></section>" },
  "el-button": true, "el-alert": true, "el-table": true, "el-table-column": true, "el-tag": true,
};

describe("Dashboard UI-03 migration", () => {
  it("uses the shared page header, metric and surface patterns", () => {
    const wrapper = shallowMount(Dashboard, { global: { stubs: sharedStubs } });
    expect(wrapper.findComponent(PageHeader).exists()).toBe(true);
    expect(wrapper.findAllComponents(MetricCard)).toHaveLength(5);
    expect(wrapper.findAllComponents(SurfaceCard)).toHaveLength(2);
    expect(wrapper.findComponent(PageHeader).props("title")).toBe("平台工作台");
    expect(wrapper.findComponent(SurfaceCard).props("title")).toBe("最近执行");
    expect(wrapper.findAllComponents(SurfaceCard)[1].props("title")).toBe("常用入口");
  });

  it("keeps dashboard empty state and quick navigation visible", async () => {
    const wrapper = shallowMount(Dashboard, {
      global: { stubs: {
        ...sharedStubs,
        "el-empty": { template: "<div>{{ description }}</div>", props: ["description"] },
      } },
    });
    await vi.waitFor(() => expect((wrapper.vm as any).loading).toBe(false));
    expect(wrapper.text()).toContain("暂无运行记录");
    expect(wrapper.text()).toContain("智能体管理");
    expect(wrapper.text()).toContain("工具管理");
    expect(wrapper.text()).toContain("运行记录");
  });
});
