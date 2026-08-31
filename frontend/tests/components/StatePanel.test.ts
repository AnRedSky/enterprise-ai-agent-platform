import { describe, expect, it } from "vitest";
import { shallowMount } from "@vue/test-utils";
import StatePanel from "@/components/ui/StatePanel.vue";

describe("StatePanel", () => {
  const mountState = (state: "loading" | "empty" | "error" | "permission" | "success") => shallowMount(StatePanel, {
    props: { state, title: `title-${state}`, description: `description-${state}`, actionLabel: state === "error" ? "重试" : undefined },
    global: { stubs: { "el-icon": true, "el-button": { template: "<button @click=\"$emit('click')\"><slot /></button>" } } },
  });

  it.each(["loading", "empty", "error", "permission", "success"] as const)("renders %s as a first-class state", (state) => {
    const wrapper = mountState(state);
    expect(wrapper.classes()).toContain(`state-panel--${state}`);
    expect(wrapper.text()).toContain(`title-${state}`);
    expect(wrapper.text()).toContain(`description-${state}`);
  });

  it("emits action for recoverable error state", async () => {
    const wrapper = mountState("error");
    await wrapper.find("button").trigger("click");
    expect(wrapper.emitted("action")).toHaveLength(1);
  });
});
