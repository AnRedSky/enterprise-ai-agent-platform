<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { workflowApi, type Workflow, type WorkflowExecution } from "@/api/workflows";

const route = useRoute();
const router = useRouter();
const workflows = ref<Workflow[]>([]);
const selectedWorkflowId = ref("");
const executions = ref<WorkflowExecution[]>([]);
const loading = ref(false);
const actionLoading = ref(false);
const error = ref(false);

const selectedWorkflow = computed(() => workflows.value.find((item) => item.id === selectedWorkflowId.value) || null);
const latestExecution = computed(() => executions.value[0] || null);
const statusLabel = (status?: string) => ({ pending: "等待运行", running: "运行中", completed: "已完成", failed: "失败", cancelled: "已取消" }[status || ""] || `未知状态（${status || "unknown"}）`);
const statusType = (status?: string) => status === "failed" ? "danger" : status === "running" || status === "pending" ? "warning" : status === "completed" ? "success" : "info";
const activeIndex = computed(() => { const status = selectedWorkflow.value?.status || "draft"; if (latestExecution.value?.status === "failed") return 4; if (latestExecution.value) return 3; if (status === "published") return 2; return status === "draft" ? 0 : 1; });

async function load() {
  loading.value = true; error.value = false;
  try {
    workflows.value = await workflowApi.list();
    const routeWorkflowId = typeof route.query.workflow_id === "string" ? route.query.workflow_id : "";
    selectedWorkflowId.value = routeWorkflowId && workflows.value.some((item) => item.id === routeWorkflowId) ? routeWorkflowId : workflows.value[0]?.id || "";
    await loadExecutions();
  } catch (err) { console.error("工作流生命周期上下文加载失败", err); error.value = true; }
  finally { loading.value = false; }
}

async function loadExecutions() {
  if (!selectedWorkflowId.value) { executions.value = []; return; }
  try {
    executions.value = (await workflowApi.listExecutions(selectedWorkflowId.value)).sort((a, b) => b.created_at.localeCompare(a.created_at));
  } catch (err) { console.warn("工作流运行状态加载失败", err); executions.value = []; }
}

async function selectWorkflow(id: string) {
  selectedWorkflowId.value = id;
  await loadExecutions();
  void router.replace({ path: "/workflows", query: { workflow_id: id } });
}

async function executeAction(action: "run" | "cancel" | "retry" | "resume") {
  if (!latestExecution.value) return;
  actionLoading.value = true;
  try {
    const id = latestExecution.value.id;
    if (action === "run") await workflowApi.runExecution(id);
    if (action === "cancel") await workflowApi.cancelExecution(id);
    if (action === "retry") await workflowApi.retryExecution(id);
    if (action === "resume") await workflowApi.resumeExecution(id);
    await loadExecutions();
    ElMessage.success(action === "run" ? "Execution 已进入运行流程" : action === "cancel" ? "Execution 已取消" : action === "retry" ? "已创建 Retry Execution" : "已创建 Resume Execution");
  } catch (err) { console.error(`Workflow execution ${action} failed`, err); ElMessage.error("Execution 操作失败，请稍后重试"); }
  finally { actionLoading.value = false; }
}

function openRuntime() {
  if (!latestExecution.value) return;
  void router.push({ path: "/runtime", query: { execution_id: latestExecution.value.id, workflow_id: selectedWorkflowId.value, source: "workflow-lifecycle" } });
}

onMounted(load);
</script>

<template>
  <section class="lifecycle-panel" aria-label="工作流生命周期工作台">
    <div class="panel-head"><div><span class="eyebrow">P1.1 生命周期</span><h2>工作流发布与运行闭环</h2><p>生命周期阶段与真实 Workflow Execution 状态联动，失败后可直接 Retry / Resume。</p></div><el-tag effect="plain">当前阶段：{{ ["草稿", "版本", "已发布", "运行", "恢复"][activeIndex] }}</el-tag></div>
    <el-alert v-if="error" title="工作流生命周期上下文加载失败，请刷新后重试" type="warning" :closable="false" show-icon />
    <div v-else class="context-row"><el-select :model-value="selectedWorkflowId" placeholder="选择工作流" :loading="loading" @update:model-value="selectWorkflow"><el-option v-for="workflow in workflows" :key="workflow.id" :label="workflow.name" :value="workflow.id" /></el-select><div v-if="selectedWorkflow" class="workflow-state"><span>工作流状态</span><el-tag :type="statusType(selectedWorkflow.status)">{{ statusLabel(selectedWorkflow.status) }}</el-tag></div><div v-if="latestExecution" class="workflow-state"><span>最近 Execution</span><el-tag :type="statusType(latestExecution.status)">{{ statusLabel(latestExecution.status) }}</el-tag></div></div>
    <div class="steps"><div v-for="(stage, index) in [{ key: 'draft', label: '草稿', description: '编辑工作流定义与版本' }, { key: 'versioned', label: '版本', description: '创建可追踪版本' }, { key: 'published', label: '已发布', description: '确定当前生效版本' }, { key: 'running', label: '运行', description: '创建并观察 Execution' }, { key: 'recovery', label: '恢复', description: '失败后 Retry / Resume' }]" :key="stage.key" :class="['step', { active: index === activeIndex, done: index < activeIndex }]" @click="index >= 3 ? openRuntime() : undefined"><span>{{ index + 1 }}</span><div><strong>{{ stage.label }}</strong><small>{{ stage.description }}</small></div></div></div>
    <div v-if="latestExecution" class="execution-row"><div><span>最新运行</span><strong>{{ latestExecution.id }}</strong><small>{{ statusLabel(latestExecution.status) }} · {{ latestExecution.created_at }}</small></div><div class="execution-actions"><el-button v-if="latestExecution.status === 'pending'" size="small" type="primary" :loading="actionLoading" @click="executeAction('run')">运行</el-button><el-button v-if="latestExecution.status === 'pending' || latestExecution.status === 'running'" size="small" type="warning" :loading="actionLoading" @click="executeAction('cancel')">取消</el-button><el-button v-if="latestExecution.status === 'failed'" size="small" :loading="actionLoading" @click="executeAction('retry')">Retry</el-button><el-button v-if="latestExecution.status === 'failed'" size="small" :loading="actionLoading" @click="executeAction('resume')">Resume</el-button><el-button size="small" plain @click="openRuntime">查看运行诊断</el-button></div></div>
    <div class="actions"><span>版本 → 发布 → Trigger → Execution → Trace → Audit</span><el-button size="small" @click="router.push('/workflows/triggers')">管理触发器</el-button></div>
  </section>
</template>

<style scoped>
.lifecycle-panel{position:fixed;right:24px;bottom:20px;z-index:1000;width:min(820px,calc(100vw - 48px));padding:20px 22px;border:1px solid #d0d5dd;border-radius:12px;background:rgba(255,255,255,.98);box-shadow:0 12px 32px rgba(16,24,40,.16)}.panel-head{display:flex;justify-content:space-between;gap:20px}.eyebrow{font-size:10px;color:#667085;font-weight:700;letter-spacing:.08em}.panel-head h2{margin:4px 0;font-size:17px;color:#1d2939}.panel-head p{margin:0;color:#667085;font-size:12px}.context-row{display:flex;gap:10px;align-items:center;margin-top:16px}.context-row :deep(.el-select){width:240px}.workflow-state{display:flex;gap:7px;align-items:center;padding:7px 10px;border:1px solid #eaecf0;border-radius:8px}.workflow-state span{font-size:10px;color:#667085}.steps{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:14px}.step{display:flex;gap:8px;min-height:58px;padding:10px;border:1px solid #eaecf0;border-radius:9px;background:#fcfcfd}.step span{display:grid;place-items:center;width:22px;height:22px;flex:0 0 22px;border-radius:50%;background:#f2f4f7;color:#667085;font-size:10px;font-weight:700}.step strong,.step small{display:block}.step strong{font-size:11px;color:#344054}.step small{margin-top:3px;color:#667085;font-size:9px;line-height:1.4}.step.active{border-color:#b8c7e6;background:#eff6ff}.step.active span,.step.done span{background:#2563eb;color:#fff}.step:nth-child(n+4){cursor:pointer}.execution-row{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-top:12px;padding:11px 13px;border:1px solid #eaecf0;border-radius:9px}.execution-row span,.execution-row strong,.execution-row small{display:block}.execution-row span{font-size:9px;color:#667085}.execution-row strong{margin:2px 0;font-size:11px;color:#344054;max-width:360px;overflow:hidden;text-overflow:ellipsis}.execution-row small{font-size:9px;color:#667085}.execution-actions{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}.actions{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-top:12px;padding-top:11px;border-top:1px solid #f2f4f7;color:#667085;font-size:10px}@media(max-width:900px){.lifecycle-panel{right:12px;bottom:12px;width:calc(100vw - 24px)}.steps{grid-template-columns:1fr}.context-row,.execution-row{align-items:flex-start;flex-direction:column}.context-row :deep(.el-select){width:100%}.actions{align-items:flex-start;flex-direction:column}}
</style>
