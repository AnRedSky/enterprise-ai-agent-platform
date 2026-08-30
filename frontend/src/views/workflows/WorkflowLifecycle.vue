<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { workflowApi, type Workflow, type WorkflowExecution, type WorkflowTrigger, type SchedulerStatus, type WorkflowVersion } from "@/api/workflows";

const route = useRoute();
const router = useRouter();
const workflows = ref<Workflow[]>([]);
const versions = ref<WorkflowVersion[]>([]);
const triggers = ref<WorkflowTrigger[]>([]);
const schedules = ref<Record<string, SchedulerStatus>>({});
const executions = ref<WorkflowExecution[]>([]);
const selectedId = ref(typeof route.query.workflow_id === "string" ? route.query.workflow_id : "");
const loading = ref(false);
const detailLoading = ref(false);

const selected = computed(() => workflows.value.find((item) => item.id === selectedId.value));
const publishedVersion = computed(() => versions.value.find((item) => item.id === selected.value?.published_version_id));
const latestExecution = computed(() => executions.value[0]);
const lifecycleSteps = computed(() => [
  { label: "工作流", done: Boolean(selected.value), active: false },
  { label: "版本", done: Boolean(publishedVersion.value), active: Boolean(selected.value) && !publishedVersion.value },
  { label: "发布", done: selected.value?.status === "published", active: Boolean(publishedVersion.value) && selected.value?.status !== "published" },
  { label: "触发器", done: triggers.value.length > 0, active: selected.value?.status === "published" && triggers.value.length === 0 },
  { label: "运行", done: executions.value.length > 0, active: selected.value?.status === "published" && executions.value.length === 0 },
]);

const statusText: Record<string, string> = {
  draft: "草稿", published: "已发布", archived: "已归档", pending: "等待中", running: "运行中",
  completed: "已完成", failed: "失败", cancelled: "已取消", retrying: "重试中", skipped: "已跳过",
  enabled: "已启用", disabled: "已停用",
};
const triggerTypeText: Record<string, string> = { manual: "手动", scheduled: "定时", webhook: "Webhook" };
const displayStatus = (value?: string) => value ? statusText[value] || `未知状态（${value}）` : "-";
const displayTriggerType = (value?: string) => value ? triggerTypeText[value] || `未知类型（${value}）` : "-";
const formatTime = (value?: string | null) => value ? new Date(value).toLocaleString("zh-CN", { hour12: false }) : "-";

async function load() {
  loading.value = true;
  try {
    workflows.value = (await workflowApi.list()).data;
    const requestedId = typeof route.query.workflow_id === "string" ? route.query.workflow_id : "";
    if (requestedId && workflows.value.some((item) => item.id === requestedId)) selectedId.value = requestedId;
    else if (!selectedId.value || !workflows.value.some((item) => item.id === selectedId.value)) selectedId.value = workflows.value[0]?.id || "";
    if (selectedId.value) await loadDetails(selectedId.value);
  } catch {
    ElMessage.error("工作流生命周期数据加载失败，请刷新后重试");
  } finally {
    loading.value = false;
  }
}

async function loadDetails(id: string) {
  detailLoading.value = true;
  try {
    const [versionResponse, triggerResponse, executionResponse] = await Promise.all([
      workflowApi.versions(id),
      workflowApi.triggers(id),
      workflowApi.listExecutions(id),
    ]);
    versions.value = versionResponse.data;
    triggers.value = triggerResponse.data;
    executions.value = executionResponse.data;
    const scheduled = triggers.value.filter((item) => item.trigger_type === "scheduled");
    const results = await Promise.all(scheduled.map(async (trigger) => [trigger.id, (await workflowApi.schedule(id, trigger.id)).data] as const));
    schedules.value = Object.fromEntries(results);
  } catch {
    versions.value = [];
    triggers.value = [];
    executions.value = [];
    schedules.value = {};
    ElMessage.error("工作流生命周期详情加载失败，请稍后重试");
  } finally {
    detailLoading.value = false;
  }
}

async function selectWorkflow(id: string) {
  selectedId.value = id;
  await loadDetails(id);
}

function openRuntimeExecution(execution: WorkflowExecution) {
  void router.push({
    path: "/runtime",
    query: {
      tab: "executions",
      source: "workflow-lifecycle",
      execution_id: execution.id,
      workflow_id: execution.workflow_id,
      workflow_version_id: execution.workflow_version_id,
    },
  });
}

function openScheduledExecution(executionId?: string | null) {
  if (!executionId) return;
  void router.push({
    path: "/runtime",
    query: {
      tab: "executions",
      source: "workflow-lifecycle",
      execution_id: executionId,
      ...(selected.value ? { workflow_id: selected.value.id } : {}),
    },
  });
}

onMounted(load);
</script>

<template>
  <main class="lifecycle-page" aria-label="工作流生命周期工作台">
    <header class="page-header">
      <div>
        <span class="eyebrow">P1 生命周期治理</span>
        <h1>Workflow 生命周期工作台</h1>
        <p>把定义、版本、发布、触发器、调度与真实 Execution 串成一条可验证的运行链路。</p>
      </div>
      <el-button :loading="loading" @click="load">刷新</el-button>
    </header>

    <el-card class="workflow-selector" shadow="never">
      <div v-if="selected" class="workflow-identity" aria-label="当前工作流">
        <strong class="workflow-name">{{ selected.name }}</strong>
        <span class="identifier">工作流 ID：{{ selected.id }}</span>
      </div>
      <el-select :model-value="selectedId" placeholder="选择工作流" filterable @update:model-value="selectWorkflow">
        <el-option v-for="item in workflows" :key="item.id" :label="item.name" :value="item.id" />
      </el-select>
      <el-tag v-if="selected" effect="plain">{{ displayStatus(selected.status) }}</el-tag>
    </el-card>

    <el-empty v-if="!loading && !workflows.length" description="暂无工作流，请先创建工作流。" />

    <template v-if="selected">
      <section class="lifecycle-card" aria-label="生命周期阶段">
        <div v-for="(step, index) in lifecycleSteps" :key="step.label" class="step" :class="{ done: step.done, active: step.active }">
          <span class="step-index">{{ step.done ? "✓" : index + 1 }}</span>
          <strong>{{ step.label }}</strong>
          <span>{{ step.done ? "已完成" : step.active ? "当前关注" : "待进入" }}</span>
          <i v-if="index < lifecycleSteps.length - 1">→</i>
        </div>
      </section>

      <el-row :gutter="16" v-loading="detailLoading">
        <el-col :xs="24" :lg="14">
          <el-card shadow="never">
            <template #header><div class="card-header"><strong>版本与发布</strong><span>当前生效版本</span></div></template>
            <el-descriptions v-if="publishedVersion" :column="2" border>
              <el-descriptions-item label="版本">v{{ publishedVersion.version }}</el-descriptions-item>
              <el-descriptions-item label="状态"><el-tag type="success">{{ displayStatus(publishedVersion.status) }}</el-tag></el-descriptions-item>
              <el-descriptions-item label="版本标识">{{ publishedVersion.id }}</el-descriptions-item>
              <el-descriptions-item label="发布时间">{{ formatTime(publishedVersion.created_at) }}</el-descriptions-item>
            </el-descriptions>
            <el-empty v-else description="尚未发布可生效版本" />
          </el-card>
        </el-col>
        <el-col :xs="24" :lg="10">
          <el-card shadow="never">
            <template #header><div class="card-header"><strong>最近运行</strong><span>{{ executions.length }} 条</span></div></template>
            <template v-if="latestExecution">
              <div class="execution-line"><el-tag>{{ displayStatus(latestExecution.status) }}</el-tag><strong>{{ latestExecution.id }}</strong></div>
              <div class="muted">创建于 {{ formatTime(latestExecution.created_at) }}</div>
              <div v-if="latestExecution.current_node_id" class="muted">当前节点：{{ latestExecution.current_node_id }}</div>
              <div v-if="latestExecution.error_code" class="error-code">错误代码：{{ latestExecution.error_code }}</div>
              <div class="execution-actions"><el-button size="small" type="primary" plain @click="openRuntimeExecution(latestExecution)">进入 Runtime 诊断</el-button></div>
            </template>
            <el-empty v-else description="暂无运行记录" />
          </el-card>
        </el-col>
      </el-row>

      <el-card class="trigger-card" shadow="never" v-loading="detailLoading">
        <template #header><div class="card-header"><strong>触发与调度</strong><span>以真实后端 Trigger / Scheduler 状态为准</span></div></template>
        <el-table v-if="triggers.length" :data="triggers" border>
          <el-table-column prop="name" label="触发器" min-width="180" />
          <el-table-column label="类型" width="110"><template #default="{ row }">{{ displayTriggerType(row.trigger_type) }}</template></el-table-column>
          <el-table-column label="状态" width="110"><template #default="{ row }"><el-tag :type="row.status === 'enabled' ? 'success' : 'info'">{{ displayStatus(row.status) }}</el-tag></template></el-table-column>
          <el-table-column label="下次运行" min-width="180"><template #default="{ row }">{{ row.trigger_type === 'scheduled' ? formatTime(schedules[row.id]?.next_run_at) : '-' }}</template></el-table-column>
          <el-table-column label="最近运行" min-width="180"><template #default="{ row }">{{ row.trigger_type === 'scheduled' ? formatTime(schedules[row.id]?.last_run_at) : '-' }}</template></el-table-column>
          <el-table-column label="最近 Execution" min-width="220"><template #default="{ row }"><el-button v-if="schedules[row.id]?.last_execution_id" link type="primary" @click="openScheduledExecution(schedules[row.id]?.last_execution_id)">{{ schedules[row.id]?.last_execution_id }}</el-button><span v-else>-</span></template></el-table-column>
        </el-table>
        <el-empty v-else description="暂无触发器，发布工作流后可配置手动、定时或 Webhook 入口。" />
      </el-card>

      <el-alert v-if="selected.status === 'archived'" title="该工作流已归档，生命周期数据保持可观测但不再允许继续变更。" type="warning" :closable="false" show-icon />
    </template>
  </main>
</template>

<style scoped>
.lifecycle-page{padding:24px 32px;background:#f7f8fa;min-height:100%}.page-header{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;margin-bottom:16px}.eyebrow{font-size:11px;font-weight:700;letter-spacing:.08em;color:#667085}.page-header h1{margin:5px 0;font-size:24px;color:#101828}.page-header p{margin:0;color:#667085;font-size:13px}.workflow-selector{display:flex;align-items:center;gap:16px;margin-bottom:16px}.workflow-identity{display:flex;flex-direction:column;gap:3px;min-width:220px}.workflow-name{font-size:14px;color:#101828;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.workflow-selector .el-select{width:320px}.identifier,.muted{font-size:12px;color:#667085}.lifecycle-card{display:flex;align-items:center;gap:4px;padding:18px;margin-bottom:16px;background:#fff;border:1px solid #eaecf0;border-radius:10px}.step{position:relative;display:flex;align-items:center;gap:7px;flex:1;color:#98a2b3;font-size:12px}.step strong{color:#667085}.step.done strong,.step.active strong{color:#1d2939}.step-index{width:24px;height:24px;border-radius:50%;display:grid;place-items:center;border:1px solid #d0d5dd;font-size:11px}.step.done .step-index{background:#ecfdf3;border-color:#abefc6;color:#067647}.step.active .step-index{border-color:#84adff;color:#175cd3}.step i{margin-left:auto;font-style:normal;color:#98a2b3}.card-header{display:flex;justify-content:space-between;align-items:center}.card-header span{font-size:12px;color:#667085}.execution-line{display:flex;align-items:center;gap:10px;margin-bottom:8px}.execution-line strong{font-size:12px;word-break:break-all}.execution-actions{display:flex;justify-content:flex-end;margin-top:12px}.error-code{margin-top:10px;font-size:12px;color:#b42318}.trigger-card{margin-top:16px}.lifecycle-page>.el-alert{margin-top:16px}@media(max-width:900px){.lifecycle-page{padding:16px}.page-header{flex-direction:column}.workflow-selector{flex-wrap:wrap}.workflow-identity{min-width:0;width:100%}.workflow-selector .el-select{width:100%}.lifecycle-card{display:grid;grid-template-columns:1fr 1fr}.step i{display:none}.execution-actions{justify-content:flex-start}}
</style>
