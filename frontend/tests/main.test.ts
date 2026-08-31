import { describe, expect, it, vi } from "vitest";

const directive = { mounted: vi.fn(), updated: vi.fn(), unmounted: vi.fn() };
const app = { component: vi.fn(), directive: vi.fn(), use: vi.fn().mockReturnThis(), mount: vi.fn() };

vi.mock("vue", () => ({ createApp: vi.fn(() => app) }));
vi.mock("pinia", () => ({ createPinia: vi.fn(() => ({ name: "pinia" })) }));
vi.mock("element-plus", () => {
  const component = {};
  return {
    ElAlert: component, ElButton: component, ElCard: component, ElCol: component, ElDescriptions: component, ElDescriptionsItem: component,
    ElDialog: component, ElDivider: component, ElDrawer: component, ElEmpty: component, ElForm: component, ElFormItem: component, ElIcon: component,
    ElInput: component, ElInputNumber: component, ElOption: component, ElPagination: component, ElRow: component, ElScrollbar: component, ElSelect: component,
    ElSlider: component, ElSwitch: component, ElTable: component, ElTableColumn: component, ElTabPane: component, ElTabs: component, ElTag: component,
    ElTimeline: component, ElTimelineItem: component, vLoading: directive,
  };
});
vi.mock("@/App.vue", () => ({ default: {} }));
vi.mock("@/router", () => ({ default: {} }));

describe("frontend bootstrap", () => {
  it("registers Element Plus loading directive globally", async () => {
    await import("@/main");
    expect(app.directive).toHaveBeenCalledWith("loading", directive);
  });
});
