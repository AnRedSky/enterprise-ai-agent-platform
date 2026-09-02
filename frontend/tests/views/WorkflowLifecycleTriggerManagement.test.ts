import { mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import WorkflowLifecycle from "@/views/workflows/WorkflowLifecycle.vue";

const router = { push: vi.fn(), replace: vi.fn() };
const workflowApi = {
  list: vi.fn(),
  versions: vi.fn(),
  triggers: vi.fn(),
  listExecutions: vi.fn(),
  schedule: vi.fn(),
  updateTrigger: vi.fn(),
  deleteTrigger: vi.fn(),
  invokeTrigger: vi.fn(),
  runExecution: vi.fn(),
  cancelExecution: vi.fn(),
  retryExecution: vi.fn(),
  resumeExecution: vi.fn(),
};

vi.mock("vue-router", () => ({
  useRoute: () => ({ query: {} }),
  useRouter: () => router,
}));
vi.mock("@/api/workflows", () => ({ workflowApi }));
vi.mock("element-plus", () => ({ ElMessage: { success: vi.fn(), error: vi.fn() } }));

const workflow = { id: "w1", name: "Workflow 1", description: "", owner_id: "u1", tenant_id: "t1", status: "published", published_version_id: "v1", created_at: "2026-01-01", updated_at: "2026-01-01" };
const version = { id: "v1", workflow_id: "w1", version: 1, definition: {}, status: "published", created_by: "u1", created_at: "2026-01-01" };
const scheduledTrigger = { id: "t-scheduled", tenant_id: "t1", workflow_id: "w1", name: "Daily", trigger_type: "scheduled", status: "enabled", config: { timezone: "Asia/Seoul", interval_seconds: 600, misfire_policy: "catch_up", catch_up_limit: 5 }, created_by: "u1", created_at: "2026-01-01", updated_at: "2026-01-01" };
const webhookTrigger = { id: "t-webhook", tenant_id: "t1", workflow_id: "w1", name: "Webhook", trigger_type: "webhook", status: "enabled", config: { auth_mode: "secret", event_id_field: "event_id", secret_configured: true }, created_by: "u1", created_at: "2026-01-01", updated_at: "2026-01-01" };

function mountPage() {
  return mount(WorkflowLifecycle, {
    global: {
      stubs: {
        PageHeader: true,
        SurfaceCard: true,
        StatePanel: true,
        ConfirmDialog: true,
        "el-button": true,
        "el-select": true,
        "el-option": true,
        "el-tag": true,
        "el-descriptions": true,
        "el-descriptions-item": true,
        "el-empty": true,
        "el-table": true,
        "el-table-column": true,
        "el-alert": true,
        "el-dialog": true,
        "el-form": true,
        "el-form-item": true,
        "el-input": true,
        "el-input-number": true,
      },
    },
  });
}

describe("WorkflowLifecycle trigger management", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    workflowApi.list.mockResolvedValue({ data: [workflow] });
    workflowApi.versions.mockResolvedValue({ data: [version] });
    workflowApi.triggers.mockResolvedValue({ data: [scheduledTrigger, webhookTrigger] });
    workflowApi.listExecutions.mockResolvedValue({ data: [] });
    workflowApi.schedule.mockResolvedValue({ data: { id: "s1" } });
    workflowApi.updateTrigger.mockResolvedValue({ data: scheduledTrigger });
    workflowApi.deleteTrigger.mockResolvedValue({ data: undefined });
  });

  it("opens scheduled Trigger editor with backend durable configuration", async () => {
    const wrapper = mountPage();
    await (wrapper.vm as any).load();
    await (wrapper.vm as any).openTriggerEditor(scheduledTrigger);

    expect((wrapper.vm as any).triggerEditor.value.trigger.id).toBe("t-scheduled");
    expect((wrapper.vm as any).triggerEditor.value.timezone).toBe("Asia/Seoul");
    expect((wrapper.vm as any).triggerEditor.value.interval_seconds).toBe(600);
    expect((wrapper.vm as any).triggerEditor.value.misfire_policy).toBe("catch_up");
    expect((wrapper.vm as any).triggerEditor.value.catch_up_limit).toBe(5);
  });

  it("updates scheduled Trigger through the real PATCH contract and refreshes details", async () => {
    const wrapper = mountPage();
    await (wrapper.vm as any).load();
    await (wrapper.vm as any).openTriggerEditor(scheduledTrigger);
    (wrapper.vm as any).triggerEditor.value.interval_seconds = 900;
    await (wrapper.vm as any).saveTriggerEditor();

    expect(workflowApi.updateTrigger).toHaveBeenCalledWith("w1", "t-scheduled", {
      name: "Daily",
      config: { timezone: "Asia/Seoul", interval_seconds: 900, misfire_policy: "catch_up", catch_up_limit: 5 },
    });
    expect(workflowApi.triggers).toHaveBeenCalledTimes(2);
    expect((wrapper.vm as any).triggerEditor.value.trigger).toBeNull();
  });

  it("updates Webhook Trigger without reading or sending the existing Secret", async () => {
    const wrapper = mountPage();
    await (wrapper.vm as any).load();
    await (wrapper.vm as any).openTriggerEditor(webhookTrigger);
    (wrapper.vm as any).triggerEditor.value.event_id_field = "event_id_v2";
    await (wrapper.vm as any).saveTriggerEditor();

    expect(workflowApi.updateTrigger).toHaveBeenCalledWith("w1", "t-webhook", {
      name: "Webhook",
      config: { auth_mode: "secret", event_id_field: "event_id_v2" },
    });
  });

  it("requires explicit delete confirmation and closes the target state on cancel", async () => {
    const wrapper = mountPage();
    await (wrapper.vm as any).load();
    await (wrapper.vm as any).requestDeleteTrigger(scheduledTrigger);

    expect((wrapper.vm as any).deleteTriggerTarget.value.id).toBe("t-scheduled");
    await (wrapper.vm as any).cancelDeleteTrigger();

    expect(workflowApi.deleteTrigger).not.toHaveBeenCalled();
    expect((wrapper.vm as any).deleteTriggerTarget.value).toBeNull();
  });

  it("deletes Trigger through the real DELETE contract and refreshes details", async () => {
    const wrapper = mountPage();
    await (wrapper.vm as any).load();
    await (wrapper.vm as any).requestDeleteTrigger(webhookTrigger);
    await (wrapper.vm as any).confirmDeleteTrigger();

    expect(workflowApi.deleteTrigger).toHaveBeenCalledWith("w1", "t-webhook");
    expect(workflowApi.triggers).toHaveBeenCalledTimes(2);
    expect((wrapper.vm as any).deleteTriggerTarget.value).toBeNull();
  });
});
