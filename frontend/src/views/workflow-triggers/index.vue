<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { workflowApi, type ScheduledTriggerConfig, type SchedulerStatus, type WebhookTriggerConfig, type Workflow, type WorkflowExecution, type WorkflowTrigger, type WorkflowTriggerType } from "@/api/workflows";
import PageHeader from "@/components/ui/PageHeader.vue";
import StatePanel from "@/components/ui/StatePanel.vue";
import SurfaceCard from "@/components/ui/SurfaceCard.vue";

const router = useRouter();
const workflows = ref<Workflow[]>([]);
const triggers = ref<WorkflowTrigger[]>([]);
const selectedWorkflowId = ref("");
const pageState = ref<"loading" | "empty" | "error" | "permission" | "success">("loading");
const triggerState = ref<"loading" | "empty" | "error" | "permission" | "success">("empty");
const schedulerState = ref<"idle" | "loading" | "error" | "success">("idle");
const loading = ref(false);
const schedulerLoading = ref(false);
const saving = ref(false);
const actionKey = ref("");
const execution = ref<WorkflowExecution>();
const schedulerStatus = ref<SchedulerStatus>();
const selectedSchedulerTriggerId = ref("");
const webhookSecret = ref("");
const editingTriggerId = ref("");
const form = ref({ name: "", triggerType: "manual" as WorkflowTriggerType, configText: "{}" });
const inputText = ref("{}");

const defaultSchedule = (): ScheduledTriggerConfig => ({ timezone: "UTC", interval_seconds: 60 });
const defaultWebhook = (): Record<string, unknown> => ({ auth_mode: "secret", event_id_field: "event_id" });
function isScheduled(trigger: WorkflowTrigger) { return trigger.trigger_type === "scheduled"; }
function isWebhook(trigger: WorkflowTrigger) { return trigger.trigger_type === "webhook"; }
function scheduleConfig(trigger: WorkflowTrigger): ScheduledTriggerConfig { const config = trigger.config as Partial<ScheduledTriggerConfig>; return { timezone: typeof config.timezone === "string" ? config.timezone : "UTC", interval_seconds: typeof config.interval_seconds === "number" ? config.interval_seconds : 60, misfire_policy: config.misfire_policy, catch_up_limit: config.catch_up_limit }; }
function webhookConfig(trigger: WorkflowTrigger): WebhookTriggerConfig { const config = trigger.config as Partial<WebhookTriggerConfig>; return { auth_mode: "secret", event_id_field: typeof config.event_id_field === "string" ? config.event_id_field : "event_id", secret_configured: config.secret_configured === true }; }
function validateSchedule(config: Record<string, unknown>) { if (typeof config.timezone !== "string" || !config.timezone.trim()) throw new Error("Schedule timezone 必须是非空字符串"); if (!Number.isInteger(config.interval_seconds) || Number(config.interval_seconds) < 1) throw new Error("Schedule interval_seconds 必须是大于 0 的整数"); }
function validateWebhook(config: Record<string, unknown>, requireSecret = true) { if (requireSecret && (webhookSecret.value.length < 16 || webhookSecret.value.length > 256)) throw new Error("Webhook secret 长度必须为 16-256 个字符"); if (typeof config.event_id_field !== "string" || !config.event_id_field.trim()) throw new Error("Webhook event_id_field 必须是非空字符串"); }
function webhookEndpoint(trigger: WorkflowTrigger) { return `/api/v1/webhooks/${trigger.id}`; }
function generateSecret() { webhookSecret.value = `${crypto.randomUUID()}${crypto.randomUUID().replaceAll("-", "")}`.slice(0, 64); }
function selectedWorkflow() { return workflows.value.find((item) => item.id === selectedWorkflowId.value); }
function workflowIsPublished() { return selectedWorkflow()?.status === "published"; }
function openRuntime(executionId: string, source: "scheduler" | "webhook" | "workflow-trigger") { return router.push({ path: "/runtime", query: { execution_id: executionId, workflow_id: selectedWorkflowId.value, source } }); }
function safeActionError(fallback: string, error: unknown) { return error instanceof Error && /必须|请选择|请输入/.test(error.message) ? error.message : fallback; }

async function loadWorkflows() {
  loading.value = true;
  pageState.value = "loading";
  try {
    workflows.value = (await workflowApi.list()).data;
    pageState.value = workflows.value.length ? "success" : "empty";
    if (selectedWorkflowId.value && !workflows.value.some((item) => item.id === selectedWorkflowId.value)) selectedWorkflowId.value = "";
    await loadTriggers();
  } catch (error: any) {
    workflows.value = [];
    triggers.value = [];
    selectedWorkflowId.value = "";
    pageState.value = error?.response?.status === 403 ? "permission" : "error";
    triggerState.value = "empty";
    schedulerStatus.value = undefined;
    selectedSchedulerTriggerId.value = "";
  } finally { loading.value = false; }
}

async function loadTriggers() {
  if (!selectedWorkflowId.value) {
    triggers.value = [];
    triggerState.value = "empty";
    schedulerStatus.value = undefined;
    selectedSchedulerTriggerId.value = "";
    schedulerState.value = "idle";
    return;
  }
  triggerState.value = "loading";
  try {
    triggers.value = (await workflowApi.triggers(selectedWorkflowId.value)).data;
    triggerState.value = triggers.value.length ? "success" : "empty";
    const selected = triggers.value.find((item) => item.id === selectedSchedulerTriggerId.value);
    if (!selected || !isScheduled(selected)) {
      schedulerStatus.value = undefined;
      selectedSchedulerTriggerId.value = "";
      schedulerState.value = "idle";
    }
  } catch (error: any) {
    triggers.value = [];
    triggerState.value = error?.response?.status === 403 ? "permission" : "error";
    schedulerStatus.value = undefined;
    selectedSchedulerTriggerId.value = "";
    schedulerState.value = "idle";
    if (error?.response?.status !== 403) ElMessage.error("Trigger 查询失败，请稍后重试");
  }
}

async function loadSchedule(trigger: WorkflowTrigger) {
  if (!selectedWorkflowId.value || !isScheduled(trigger) || schedulerLoading.value) return;
  selectedSchedulerTriggerId.value = trigger.id;
  schedulerLoading.value = true;
  schedulerState.value = "loading";
  schedulerStatus.value = undefined;
  try {
    for (let attempt = 1; attempt <= 4; attempt += 1) {
      try { schedulerStatus.value = (await workflowApi.schedule(selectedWorkflowId.value, trigger.id)).data; schedulerState.value = "success"; return; }
      catch (error) {
        const message = error instanceof Error ? error.message : "";
        const retryable = message.includes("Scheduler 状态尚未初始化") || message.includes("Request failed with status code 404");
        if (!retryable || attempt === 4) throw error;
        await new Promise((resolve) => window.setTimeout(resolve, 500));
      }
    }
  } catch { schedulerState.value = "error"; ElMessage.error("Scheduler 状态查询失败，请稍后重试"); }
  finally { schedulerLoading.value = false; }
}

function resetForm() { editingTriggerId.value = ""; form.value = { name: "", triggerType: "manual", configText: "{}" }; webhookSecret.value = ""; }
function selectTriggerType(type: WorkflowTriggerType) { form.value.triggerType = type; webhookSecret.value = ""; if (type === "scheduled") form.value.configText = JSON.stringify(defaultSchedule(), null, 2); else if (type === "webhook") form.value.configText = JSON.stringify(defaultWebhook(), null, 2); else form.value.configText = "{}"; }
function editTrigger(trigger: WorkflowTrigger) { editingTriggerId.value = trigger.id; form.value = { name: trigger.name, triggerType: trigger.trigger_type, configText: JSON.stringify(trigger.config, null, 2) }; webhookSecret.value = ""; window.scrollTo({ top: 0, behavior: "smooth" }); }

async function saveTrigger() {
  if (!selectedWorkflowId.value) return ElMessage.warning("请选择 Workflow");
  if (!form.value.name.trim()) return ElMessage.warning("请输入 Trigger 名称");
  if (saving.value) return;
  const wasEditing = Boolean(editingTriggerId.value);
  try {
    const config = JSON.parse(form.value.configText) as Record<string, unknown>;
    if (form.value.triggerType === "scheduled") validateSchedule(config);
    if (form.value.triggerType === "webhook") {
      const current = editingTriggerId.value ? triggers.value.find((item) => item.id === editingTriggerId.value) : undefined;
      validateWebhook(config, !current?.config || !(current.config as WebhookTriggerConfig).secret_configured || !!webhookSecret.value);
      if (webhookSecret.value) config.secret = webhookSecret.value;
    }
    saving.value = true;
    if (editingTriggerId.value) await workflowApi.updateTrigger(selectedWorkflowId.value, editingTriggerId.value, { name: form.value.name, config });
    else await workflowApi.createTrigger(selectedWorkflowId.value, { name: form.value.name, trigger_type: form.value.triggerType, config });
    resetForm();
    await loadTriggers();
    ElMessage.success(wasEditing ? "Trigger 已更新" : "Trigger 创建成功");
  } catch (error) { ElMessage.error(error instanceof SyntaxError ? "Trigger Config 不是合法 JSON" : safeActionError("Trigger 保存失败，请稍后重试", error)); }
  finally { saving.value = false; }
}

async function toggleTrigger(trigger: WorkflowTrigger) {
  if (!selectedWorkflowId.value || actionKey.value) return;
  const nextStatus = trigger.status === "enabled" ? "disabled" : "enabled";
  if (nextStatus === "enabled" && workflowIsPublished() === false) return ElMessage.warning("Workflow 尚未发布，不能启用 Trigger");
  try {
    await ElMessageBox.confirm(`确认${nextStatus === "enabled" ? "启用" : "禁用"} Trigger「${trigger.name}」？`, `${nextStatus === "enabled" ? "启用" : "禁用"} Trigger`, { type: nextStatus === "enabled" ? "warning" : "info" });
    actionKey.value = `toggle:${trigger.id}`;
    await workflowApi.updateTrigger(selectedWorkflowId.value, trigger.id, { status: nextStatus });
    await loadTriggers();
    if (trigger.id === selectedSchedulerTriggerId.value && nextStatus === "disabled") schedulerStatus.value = undefined;
    ElMessage.success(`Trigger 已${nextStatus === "enabled" ? "启用" : "禁用"}`);
  } catch (error) { if (error !== "cancel" && error !== "close") ElMessage.error("Trigger 状态更新失败，请稍后重试"); }
  finally { actionKey.value = ""; }
}

async function deleteTrigger(trigger: WorkflowTrigger) {
  if (!selectedWorkflowId.value || actionKey.value) return;
  try {
    await ElMessageBox.confirm(`删除 Trigger「${trigger.name}」将同时解除其调度/入口配置，确认继续？`, "危险操作确认", { type: "warning", confirmButtonText: "确认删除", cancelButtonText: "取消" });
    actionKey.value = `delete:${trigger.id}`;
    await workflowApi.deleteTrigger(selectedWorkflowId.value, trigger.id);
    if (trigger.id === selectedSchedulerTriggerId.value) { selectedSchedulerTriggerId.value = ""; schedulerStatus.value = undefined; schedulerState.value = "idle"; }
    if (editingTriggerId.value === trigger.id) resetForm();
    await loadTriggers();
    ElMessage.success("Trigger 已删除");
  } catch (error) { if (error !== "cancel" && error !== "close") ElMessage.error("Trigger 删除失败，请稍后重试"); }
  finally { actionKey.value = ""; }
}

async function invokeTrigger(trigger: WorkflowTrigger) {
  if (!selectedWorkflowId.value || actionKey.value) return;
  try {
    const inputData = JSON.parse(inputText.value) as Record<string, unknown>;
    actionKey.value = `invoke:${trigger.id}`;
    execution.value = (await workflowApi.invokeTrigger(selectedWorkflowId.value, trigger.id, inputData, `frontend-trigger-${crypto.randomUUID()}`)).data;
    ElMessage.success("Trigger 已调用并进入 Workflow Execution");
    await openRuntime(execution.value.id, "workflow-trigger");
  } catch (error) { ElMessage.error(error instanceof SyntaxError ? "Trigger Input 不是合法 JSON" : "Trigger 调用失败，请稍后重试"); }
  finally { actionKey.value = ""; }
}

async function openLastSchedulerExecution() { const executionId = schedulerStatus.value?.last_execution_id; if (!executionId) return ElMessage.info("暂无最近 Execution"); await openRuntime(executionId, "scheduler"); }
async function openWebhookRuntime(trigger: WorkflowTrigger) { if (!isWebhook(trigger)) return; await router.push({ path: "/runtime", query: { workflow_id: selectedWorkflowId.value, trigger_id: trigger.id, source: "webhook" } }); }
onMounted(loadWorkflows);
</script>

<template>
  <div class="trigger-page">
    <PageHeader title="Workflow Trigger Governance" description="管理 Manual / Scheduled / Webhook Trigger，并从真实 Execution ID 进入 Runtime。"><template #actions><el-button :loading="loading" @click="loadWorkflows">刷新</el-button></template></PageHeader>
    <StatePanel v-if="pageState === 'loading'" state="loading" title="正在加载 Workflow" description="正在同步当前租户可访问的 Workflow 与 Trigger。" />
    <StatePanel v-else-if="pageState === 'permission'" state="permission" title="无权查看 Workflow Trigger" description="当前账号没有访问 Workflow Trigger 的权限。" />
    <StatePanel v-else-if="pageState === 'error'" state="error" title="Workflow 查询失败" description="无法同步最新 Workflow 事实，旧数据已清空。" action-label="重试" @action="loadWorkflows" />
    <StatePanel v-else-if="pageState === 'empty'" state="empty" title="暂无 Workflow" description="请先创建 Workflow，再配置 Trigger。" />
    <template v-else>
      <SurfaceCard title="Workflow 选择" description="必须显式选择目标 Workflow；页面不会根据数组顺序自动推断目标。"><el-form label-position="top" class="selector"><el-form-item label="Workflow"><el-select v-model="selectedWorkflowId" placeholder="选择 Workflow" clearable @change="loadTriggers"><el-option v-for="workflow in workflows" :key="workflow.id" :label="`${workflow.name} (${workflow.status})`" :value="workflow.id" /></el-select></el-form-item></el-form></SurfaceCard>
      <StatePanel v-if="!selectedWorkflowId" state="empty" title="请选择 Workflow" description="选择明确的 Workflow ID 后才能读取或修改 Trigger。" />
      <template v-else>
        <SurfaceCard title="Trigger 配置" description="Webhook Secret 只在创建/替换时提交，页面不读取旧 Secret 明文。"><el-alert title="启用 Trigger 前必须先发布 Workflow。Scheduler 状态通过后端持久化状态接口读取，不由前端推断。" type="info" :closable="false" /><el-form label-position="top" inline @submit.prevent="saveTrigger"><el-form-item label="Trigger 名称"><el-input v-model="form.name" placeholder="例如：订单事件入口" /></el-form-item><el-form-item label="类型"><el-select data-testid="workflow-trigger-type-select" :model-value="form.triggerType" :disabled="!!editingTriggerId" @update:model-value="selectTriggerType"><el-option label="manual" value="manual" /><el-option label="scheduled" value="scheduled" /><el-option label="webhook" value="webhook" /></el-select></el-form-item><el-form-item v-if="form.triggerType === 'webhook'" label="Webhook Secret"><div class="secret-editor"><el-input v-model="webhookSecret" type="password" show-password placeholder="编辑时留空表示保持现有 Secret" /><el-button size="small" :disabled="saving" @click="generateSecret">生成 Secret</el-button></div></el-form-item><el-form-item label="Config JSON"><el-input v-model="form.configText" type="textarea" :rows="3" style="width: 320px" /></el-form-item><el-form-item label=" "><el-button type="primary" :loading="saving" native-type="submit">{{ editingTriggerId ? "保存修改" : "创建 Trigger" }}</el-button><el-button v-if="editingTriggerId" :disabled="saving" @click="resetForm">取消编辑</el-button></el-form-item></el-form></SurfaceCard>
        <StatePanel v-if="triggerState === 'loading'" state="loading" title="正在加载 Trigger" description="正在同步后端 Trigger 事实。" />
        <StatePanel v-else-if="triggerState === 'permission'" state="permission" title="无权访问 Trigger" description="当前账号没有访问该 Workflow Trigger 的权限。" />
        <StatePanel v-else-if="triggerState === 'error'" state="error" title="Trigger 查询失败" description="Trigger 数据已清空，避免继续展示 stale facts。" action-label="重试" @action="loadTriggers" />
        <StatePanel v-else-if="triggerState === 'empty'" state="empty" title="暂无 Trigger" description="当前 Workflow 尚未配置 Trigger。" />
        <SurfaceCard v-else title="Trigger 列表" description="所有状态和操作均以后端 durable ID 为准"><el-table :data="triggers" empty-text="暂无 Trigger"><el-table-column prop="name" label="名称" min-width="180" /><el-table-column prop="trigger_type" label="类型" width="110" /><el-table-column label="Schedule / Webhook" min-width="300"><template #default="scope"><span v-if="isScheduled(scope.row as WorkflowTrigger)">{{ scheduleConfig(scope.row as WorkflowTrigger).timezone }} / 每 {{ scheduleConfig(scope.row as WorkflowTrigger).interval_seconds }} 秒</span><span v-else-if="isWebhook(scope.row as WorkflowTrigger)">POST {{ webhookEndpoint(scope.row as WorkflowTrigger) }} / event_id: {{ webhookConfig(scope.row as WorkflowTrigger).event_id_field }}</span><span v-else>-</span></template></el-table-column><el-table-column label="状态" width="110"><template #default="scope"><el-tag :type="scope.row.status === 'enabled' ? 'success' : 'info'">{{ scope.row.status }}</el-tag></template></el-table-column><el-table-column label="Secret" width="120"><template #default="scope"><el-tag v-if="isWebhook(scope.row as WorkflowTrigger)" type="success">{{ webhookConfig(scope.row as WorkflowTrigger).secret_configured ? '已配置' : '未配置' }}</el-tag><span v-else>-</span></template></el-table-column><el-table-column prop="updated_at" label="更新时间" min-width="180" /><el-table-column label="操作" width="560"><template #default="scope"><el-button size="small" :disabled="Boolean(actionKey)" @click="editTrigger(scope.row as WorkflowTrigger)">编辑</el-button><el-button v-if="scope.row.trigger_type === 'scheduled'" size="small" :loading="schedulerLoading && selectedSchedulerTriggerId === scope.row.id" @click="loadSchedule(scope.row as WorkflowTrigger)">调度状态</el-button><el-button v-if="scope.row.trigger_type === 'scheduled' && selectedSchedulerTriggerId === scope.row.id && schedulerStatus?.last_execution_id" size="small" @click="openLastSchedulerExecution">最近 Execution</el-button><el-button v-if="scope.row.trigger_type === 'webhook'" size="small" :disabled="Boolean(actionKey)" @click="openWebhookRuntime(scope.row as WorkflowTrigger)">查看 Webhook 运行</el-button><el-button v-if="scope.row.trigger_type === 'manual'" size="small" :disabled="scope.row.status === 'disabled' || Boolean(actionKey)" :loading="actionKey === `invoke:${scope.row.id}`" @click="invokeTrigger(scope.row as WorkflowTrigger)">Invoke</el-button><el-button size="small" :disabled="Boolean(actionKey)" :loading="actionKey === `toggle:${scope.row.id}`" @click="toggleTrigger(scope.row as WorkflowTrigger)">{{ scope.row.status === 'enabled' ? '禁用' : '启用' }}</el-button><el-button size="small" type="danger" :disabled="Boolean(actionKey)" :loading="actionKey === `delete:${scope.row.id}`" @click="deleteTrigger(scope.row as WorkflowTrigger)">删除</el-button></template></el-table-column></el-table></SurfaceCard>
        <SurfaceCard v-if="selectedSchedulerTriggerId" title="Scheduler 持久化状态" description="状态来自指定 Trigger ID 的后端持久化记录"><StatePanel v-if="schedulerState === 'loading'" state="loading" title="正在读取 Scheduler 状态" description="" /><StatePanel v-else-if="schedulerState === 'error'" state="error" title="Scheduler 状态查询失败" description="无法确认最新 Scheduler 事实。" action-label="重试" @action="loadSchedule(triggers.find((item) => item.id === selectedSchedulerTriggerId) as WorkflowTrigger)" /><template v-else-if="schedulerStatus"><el-descriptions :column="3" border><el-descriptions-item label="状态"><el-tag :type="schedulerStatus.status === 'enabled' ? 'success' : 'info'">{{ schedulerStatus.status }}</el-tag></el-descriptions-item><el-descriptions-item label="时区">{{ schedulerStatus.timezone }}</el-descriptions-item><el-descriptions-item label="Schedule">{{ schedulerStatus.schedule_expression || '-' }}</el-descriptions-item><el-descriptions-item label="Misfire">{{ schedulerStatus.misfire_policy }}</el-descriptions-item><el-descriptions-item label="Catch-up Limit">{{ schedulerStatus.catch_up_limit }}</el-descriptions-item><el-descriptions-item label="下次运行">{{ schedulerStatus.next_run_at || '-' }}</el-descriptions-item><el-descriptions-item label="最近运行">{{ schedulerStatus.last_run_at || '-' }}</el-descriptions-item><el-descriptions-item label="Lease">{{ schedulerStatus.lease_active ? 'active' : 'inactive' }}</el-descriptions-item><el-descriptions-item label="最近 Execution"><el-button v-if="schedulerStatus.last_execution_id" link type="primary" @click="openLastSchedulerExecution">{{ schedulerStatus.last_execution_id }}</el-button><span v-else>-</span></el-descriptions-item></el-descriptions></template><StatePanel v-else state="empty" title="暂无 Scheduler 状态" description="当前 Trigger 尚无后端 Scheduler 状态。" /></SurfaceCard>
        <SurfaceCard title="Manual Trigger Input" description="仅 Manual Trigger 使用此输入调用后端 invoke Contract"><el-input v-model="inputText" type="textarea" :rows="4" placeholder="{}" /><div class="invoke-help">Invoke 会生成独立 Idempotency-Key，并在成功后使用返回的真实 Execution ID 进入 Runtime。</div></SurfaceCard>
      </template>
    </template>
  </div>
</template>
<style scoped>.trigger-page{padding:24px;max-width:1480px;margin:0 auto}.selector{max-width:520px;margin-top:12px}.secret-editor{display:flex;gap:8px;align-items:center}.invoke-help{margin-top:8px;color:var(--ui-text-tertiary);font-size:12px}.trigger-page :deep(.el-form-item){margin-bottom:16px}</style>
