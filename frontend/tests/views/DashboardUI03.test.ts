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

describe("Dashboard UI-03 migration", () => {
  it("uses the shared page header, metric and surface patterns", () => {
    const wrapper = shallowMount(Dashboard, {
      global: {
        stubs: {
          "el-button": true,
          "el-alert": true,
          "el-table": true,
          "el-table-column": true,
          "el-empty": true,
          "el-tag": true,
        },
      },
    });

    expect(wrapper.findComponent(PageHeader).exists()).toBe(true);
    expect(wrapper.findAllComponents(MetricCard)).toHaveLength(5);
    expect(wrapper.findAllComponents(SurfaceCard)).toHaveLength(2);
    expect(wrapper.text()).toContain("平台工作台");
    expect(wrapper.text()).toContain("最近执行");
    expect(wrapper.text()).toContain("常用入口");
  });

  it("keeps dashboard empty state and quick navigation visible", async () => {
    const wrapper = shallowMount(Dashboard, {
      global: {
        stubs: {
          "el-button": true,
          "el-alert": true,
          "el-table": true,
          "el-table-column": true,
          "el-empty": { template: "<div>{{ description }}</div>", props: ["description"] },
          "el-tag": true,
        },
      },
    });
    await vi.waitFor(() => expect((wrapper.vm as any).loading).toBe(false));

    expect(wrapper.text()).toContain("暂无运行记录");
    expect(wrapper.text()).toContain("智能体管理");
    expect(wrapper.text()).toContain("工具管理");
    expect(wrapper.text()).toContain("运行记录");
  });
});
