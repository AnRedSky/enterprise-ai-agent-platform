<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { workflowApi, type ScheduledTriggerConfig, type Workflow, type WorkflowExecution, type WorkflowTrigger } from "@/api/workflows";

const workflows = ref<Workflow[]>([]);
const triggers = ref<WorkflowTrigger[]>([]);
const selectedWorkflowId = ref("");
const loading = ref(false);
const actionLoading = ref(false);
const execution = ref<WorkflowExecution>();
const form = ref({ name: "", triggerType: "manual" as "manual" | "scheduled", configText: "{}" });
const inputText = ref("{}");

const defaultSchedule = (): ScheduledTriggerConfig => ({ timezone: "UTC", interval_seconds: 60 });

function isScheduled(trigger: WorkflowTrigger) {
  return trigger.trigger_type === "scheduled";
}

function scheduleConfig(trigger: WorkflowTrigger): ScheduledTriggerConfig {
  return {
    timezone: typeof trigger.config.timezone === "string" ? trigger.config.timezone : "UTC",
    interval_seconds: typeof trigger.config.interval_seconds === "number" ? trigger.config.interval_seconds : 60,
  };
}

function validateSchedule(config: Record<string, unknown>) {
  if (typeof config.timezone !== "string" || !config.timezone.trim()) throw new Error("Schedule timezone 必须是非空字符串");
  if (!Number.isInteger(config.interval_seconds) || Number(config.interval_seconds) < 1) throw new Error("Schedule interval_seconds 必须是大于 0 的整数");
}

async function loadWorkflows() {
  loading.value = true;
  try {
    workflows.value = (await workflowApi.list()).data;
    if (!selectedWorkflowId.value && workflows.value.length) selectedWorkflowId.value = workflows.value[0].id;
    await loadTriggers();
  } catch {
    ElMessage.error("Workflow 查询失败");
  } finally {
    loading.value = false;
  }
}

async function loadTriggers() {
  if (!selectedWorkflowId.value) {
    triggers.value = [];
    return;
  }
  try {
    triggers.value = (await workflowApi.triggers(selectedWorkflowId.value)).data;
  } catch {
    ElMessage.error("Trigger 查询失败");
  }
}

function resetForm() {
  form.value = { name: "", triggerType: "manual", configText: "{}" };
}

function selectTriggerType(type: "manual" | "scheduled") {
  form.value.triggerType = type;
  form.value.configText = type === "scheduled" ? JSON.stringify(defaultSchedule(), null, 2) : "{}";
}

async function createTrigger() {
  if (!selectedWorkflowId.value) return ElMessage.warning("请选择 Workflow");
  if (!form.value.name.trim()) return ElMessage.warning("请输入 Trigger 名称");
  try {
    const config = JSON.parse(form.value.configText) as Record<string, unknown>;
    if (form.value.triggerType === "scheduled") validateSchedule(config);
    actionLoading.value = true;
    await workflowApi.createTrigger(selectedWorkflowId.value, {
      name: form.value.name,
      trigger_type: form.value.triggerType,
      config,
    });
    resetForm();
    await loadTriggers();
    ElMessage.success("Trigger 创建成功");
  } catch (error) {
    ElMessage.error(error instanceof SyntaxError ? "Trigger Config 不是合法 JSON" : error instanceof Error ? error.message : "Trigger 创建失败");
  } finally {
    actionLoading.value = false;
  }
}

async function toggleTrigger(trigger: WorkflowTrigger) {
  if (!selectedWorkflowId.value) return;
  try {
    actionLoading.value = true;
    await workflowApi.updateTrigger(selectedWorkflowId.value, trigger.id, { status: trigger.status === "enabled" ? "disabled" : "enabled" });
    await loadTriggers();
    ElMessage.success(`Trigger 已${trigger.status === "enabled" ? "禁用" : "启用"}`);
  } catch {
    ElMessage.error("Trigger 状态更新失败");
  } finally {
    actionLoading.value = false;
  }
}

async function deleteTrigger(trigger: WorkflowTrigger) {
  if (!selectedWorkflowId.value) return;
  try {
    await ElMessageBox.confirm(`确认删除 Trigger「${trigger.name}」？`, "删除 Trigger", { type: "warning" });
    actionLoading.value = true;
    await workflowApi.deleteTrigger(selectedWorkflowId.value, trigger.id);
    await loadTriggers();
    ElMessage.success("Trigger 已删除");
  } catch (error) {
    if (error !== "cancel") ElMessage.error("Trigger 删除失败");
  } finally {
    actionLoading.value = false;
  }
}

async function invokeTrigger(trigger: WorkflowTrigger) {
  if (!selectedWorkflowId.value) return;
  try {
    const inputData = JSON.parse(inputText.value) as Record<string, unknown>;
    const idempotencyKey = `frontend-trigger-${crypto.randomUUID()}`;
    actionLoading.value = true;
    execution.value = (await workflowApi.invokeTrigger(selectedWorkflowId.value, trigger.id, inputData, idempotencyKey)).data;
    ElMessage.success("Trigger 已调用并进入 Workflow Execution");
  } catch (error) {
    ElMessage.error(error instanceof SyntaxError ? "Trigger Input 不是合法 JSON" : "Trigger 调用失败");
  } finally {
    actionLoading.value = false;
  }
}

onMounted(loadWorkflows);
</script>

<template>
  <div class="trigger-page">
    <el-card v-loading="loading">
      <template #header><div class="header"><span>Workflow Trigger Governance</span><el-button size="small" @click="loadWorkflows">刷新</el-button></div></template>
      <el-alert title="Trigger 只能作用于当前 Tenant 可访问的 Workflow；Tenant 不由前端提交。Scheduled Trigger 只使用后端已定义的 timezone + interval_seconds Contract。" type="info" :closable="false" />

      <el-form label-position="top" class="selector">
        <el-form-item label="Workflow">
          <el-select v-model="selectedWorkflowId" placeholder="选择 Workflow" @change="loadTriggers">
            <el-option v-for="workflow in workflows" :key="workflow.id" :label="`${workflow.name} (${workflow.status})`" :value="workflow.id" />
          </el-select>
        </el-form-item>
      </el-form>

      <el-divider />
      <el-form label-position="top" inline @submit.prevent="createTrigger">
        <el-form-item label="Trigger 名称"><el-input v-model="form.name" placeholder="例如：订单每分钟同步" /></el-form-item>
        <el-form-item label="类型">
          <el-select :model-value="form.triggerType" @update:model-value="selectTriggerType">
            <el-option label="manual" value="manual" />
            <el-option label="scheduled" value="scheduled" />
          </el-select>
        </el-form-item>
        <el-form-item label="Config JSON"><el-input v-model="form.configText" type="textarea" :rows="3" style="width: 320px" /></el-form-item>
        <el-form-item label=" "><el-button type="primary" :loading="actionLoading" native-type="submit">创建 Trigger</el-button></el-form-item>
      </el-form>

      <el-table :data="triggers" empty-text="暂无 Trigger">
        <el-table-column prop="name" label="名称" min-width="180" />
        <el-table-column prop="trigger_type" label="类型" width="110" />
        <el-table-column label="Schedule" min-width="220">
          <template #default="scope">
            <span v-if="isScheduled(scope.row as WorkflowTrigger)">{{ scheduleConfig(scope.row as WorkflowTrigger).timezone }} / 每 {{ scheduleConfig(scope.row as WorkflowTrigger).interval_seconds }} 秒</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="scope"><el-tag :type="scope.row.status === 'enabled' ? 'success' : 'info'">{{ scope.row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" min-width="180" />
        <el-table-column label="操作" width="250">
          <template #default="scope">
            <el-button v-if="scope.row.trigger_type === 'manual'" size="small" :disabled="scope.row.status === 'disabled'" @click="invokeTrigger(scope.row as WorkflowTrigger)">Invoke</el-button>
            <el-button size="small" :loading="actionLoading" @click="toggleTrigger(scope.row as WorkflowTrigger)">{{ scope.row.status === 'enabled' ? '禁用' : '启用' }}</el-button>
            <el-button size="small" type="danger" :loading="actionLoading" @click="deleteTrigger(scope.row as WorkflowTrigger)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-divider />
      <el-form label-position="top">
        <el-form-item label="Manual Invoke Input JSON">
          <el-input v-model="inputText" type="textarea" :rows="4" />
        </el-form-item>
      </el-form>

      <el-descriptions v-if="execution" title="最近一次 Manual Trigger Execution" :column="2" border>
        <el-descriptions-item label="Execution ID">{{ execution.id }}</el-descriptions-item>
        <el-descriptions-item label="Status"><el-tag>{{ execution.status }}</el-tag></el-descriptions-item>
        <el-descriptions-item label="Workflow Version">{{ execution.workflow_version_id }}</el-descriptions-item>
        <el-descriptions-item v-if="execution.error_code" label="Error">{{ execution.error_code }}: {{ execution.error_message || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<style scoped>
.trigger-page { padding: 16px; }
.header { display: flex; align-items: center; justify-content: space-between; }
.selector { margin-top: 16px; max-width: 520px; }
.el-form--inline { align-items: end; }
</style>
