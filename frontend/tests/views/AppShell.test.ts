import { describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createRouter, createMemoryHistory } from "vue-router";
import AppShell from "@/components/AppShell.vue";

function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/dashboard", component: { template: "<div>dashboard</div>" } },
      { path: "/agents", component: { template: "<div>agents</div>" } },
      { path: "/tools", component: { template: "<div>tools</div>" } },
      { path: "/knowledge", component: { template: "<div>knowledge</div>" } },
      { path: "/workflows", component: { template: "<div>workflows</div>" } },
      { path: "/workflows/triggers", component: { template: "<div>triggers</div>" } },
      { path: "/organizations", component: { template: "<div>organizations</div>" } },
      { path: "/organizations/:id", component: { template: "<div>organization-detail</div>" } },
      { path: "/runtime", component: { template: "<div>runtime</div>" } },
      { path: "/runtime/audit", component: { template: "<div>audit</div>" } },
      { path: "/login", component: { template: "<div>login</div>" } },
    ],
  });
}

describe("AppShell", () => {
  it("展示统一平台导航与当前用户信息", async () => {
    const router = createTestRouter();
    await router.push("/dashboard");
    await router.isReady();
    localStorage.setItem("enterprise_agent_user_id", "user-001");
    localStorage.setItem("enterprise_agent_roles", JSON.stringify(["管理员"]));

    const wrapper = mount(AppShell, { global: { plugins: [router] } });

    expect(wrapper.text()).toContain("Enterprise AI");
    expect(wrapper.text()).toContain("Agent 管理");
    expect(wrapper.text()).toContain("知识库");
    expect(wrapper.text()).toContain("工作流");
    expect(wrapper.text()).toContain("组织管理");
    expect(wrapper.text()).toContain("user-001");
    expect(wrapper.text()).toContain("管理员");
    expect(wrapper.text()).toContain("本地环境");
  });

  it("点击叶子导航后更新路由", async () => {
    const router = createTestRouter();
    await router.push("/dashboard");
    await router.isReady();
    const wrapper = mount(AppShell, { global: { plugins: [router] } });

    const agentsItem = wrapper.findAll(".el-menu-item").find((item) => item.text() === "Agent 管理");
    expect(agentsItem).toBeDefined();

    await agentsItem!.trigger("click");
    await vi.waitFor(() => {
      expect(router.currentRoute.value.path).toBe("/agents");
    });
  });

  it("组织详情保持组织导航高亮并展示详情标题", async () => {
    const router = createTestRouter();
    await router.push("/organizations/org-001");
    await router.isReady();
    const wrapper = mount(AppShell, { global: { plugins: [router] } });

    expect(wrapper.find('.el-menu-item.is-active').text()).toContain("组织管理");
    expect(wrapper.text()).toContain("组织详情");
  });

  it("侧边栏折叠状态可以持久化", async () => {
    const router = createTestRouter();
    await router.push("/dashboard");
    await router.isReady();
    const wrapper = mount(AppShell, { global: { plugins: [router] } });

    await wrapper.get(".collapse-button").trigger("click");

    expect(localStorage.getItem("enterprise_agent_sidebar_collapsed")).toBe("1");
    expect(wrapper.find(".brand-copy").exists()).toBe(false);
  });
});
