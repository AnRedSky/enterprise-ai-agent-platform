import { describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import RuntimeObservabilityOverview from "@/views/runtime/components/RuntimeObservabilityOverview.vue";
import StatePanel from "@/components/ui/StatePanel.vue";

const executions = vi.fn();
vi.mock("@/api/runtime", () => ({ runtimeApi: { executions } }));
vi.mock("vue-router", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/utils/runtime", () => ({ getRuntimeStatusMeta: vi.fn() }));

function mountView() {
  return mount(RuntimeObservabilityOverview, { global: { stubs: { "el-button": true, "el-tag": true } } });
}

describe("Runtime UI-04 states", () => {
  it("renders loading then success state", async () => {
    let resolve!: (value: any) => void;
    executions.mockReturnValueOnce(new Promise((r) => { resolve = r; }));
    const wrapper = mountView();
    expect(wrapper.findComponent(StatePanel).props("state")).toBe("loading");
    resolve({ data: { items: [{ execution_id: "e1", status: "completed" }] } });
    await flushPromises();
    expect(wrapper.find(".metric-grid").exists()).toBe(true);
  });

  it.each([
    ["empty", { data: { items: [] } }, "暂无运行记录"],
    ["error", Promise.reject(new Error("network")), "运行概览加载失败"],
    ["permission", Promise.reject({ response: { status: 403 } }), "无权查看运行概览"],
  ] as const)("renders %s state", async (state, response, title) => {
    executions.mockReturnValueOnce(response);
    const wrapper = mountView();
    await flushPromises();
    expect(wrapper.findComponent(StatePanel).props("state")).toBe(state);
    expect(wrapper.text()).toContain(title);
  });
});
