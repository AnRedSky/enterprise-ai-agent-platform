<template>
  <div class="global-runtime-page">
    <div class="page-header">
      <div>
        <h2>全局 Runtime Operations</h2>
        <p>只读汇总 Workflow、Execution、Frontier、Trigger 的持久化运行事实，不重复实现生命周期。</p>
      </div>
      <div class="header-actions">
        <el-select v-model="windowHours" style="width: 130px" @change="reload">
          <el-option label="最近 1 小时" :value="1" />
          <el-option label="最近 24 小时" :value="24" />
          <el-option label="最近 7 天" :value="168" />
        </el-select>
        <el-button :icon="Refresh" :loading="loading" @click="reload">刷新</el-button>
      </div>
    </div>

    <el-alert v-if="error" type="error" :closable="false" show-icon title="全局 Runtime 数据加载失败，请稍后重试。" />

    <div v-if="posture" class="metric-grid">
      <el-card shadow="never"><span>Execution 总量</span><strong>{{ posture.executions.total }}</strong><small>{{ posture.executions.active_count }} 个活动执行</small></el-card>
      <el-card shadow="never"><span>失败 / 恢复</span><strong>{{ posture.executions.recovery_count }}</strong><small>当前窗口内失败执行</small></el-card>
      <el-card shadow="never"><span>Pending Frontier</span><strong>{{ posture.worker.pending_frontiers }}</strong><small>{{ posture.scheduler.durable_frontier_backlog }} 个调度持久化积压</small></el-card>
      <el-card shadow="never"><span>Expired Lease</span><strong>{{ posture.worker.expired_leases }}</strong><small>{{ posture.worker.active_worker_owners }} 个活动 Worker Owner</small></el-card>
    </div>

    <div v-if="posture" class="status-grid">
      <el-card shadow="never">
        <template #header><div class="card-title"><strong>Worker 运行态</strong><el-tag :type="livenessType(posture.worker.liveness)">{{ livenessLabel(posture.worker.liveness) }}</el-tag></div></template>
        <div class="status-list"><div><span>Running Frontier</span><strong>{{ posture.worker.running_frontiers }}</strong></div><div><span>Pending Frontier</span><strong>{{ posture.worker.pending_frontiers }}</strong></div><div><span>Leased Frontier</span><strong>{{ posture.worker.leased_frontiers }}</strong></div><div><span>Active Worker Owner</span><strong>{{ posture.worker.active_worker_owners }}</strong></div><div><span>过期 Lease</span><strong>{{ posture.worker.expired_leases }}</strong></div></div>
        <el-alert v-if="posture.worker.liveness === 'unknown'" class="notice" type="info" :closable="false" :title="posture.worker.liveness_reason_code || '当前没有持久化心跳事实，无法判断进程存活。'" />
      </el-card>
      <el-card shadow="never">
        <template #header><div class="card-title"><strong>Scheduler 运行态</strong><el-tag :type="livenessType(posture.scheduler.liveness)">{{ livenessLabel(posture.scheduler.liveness) }}</el-tag></div></template>
        <div class="status-list"><div><span>启用 Schedule Trigger</span><strong>{{ posture.scheduler.enabled_scheduled_triggers }}</strong></div><div><span>Durable Frontier Backlog</span><strong>{{ posture.scheduler.durable_frontier_backlog }}</strong></div></div>
        <el-alert v-if="posture.scheduler.liveness === 'unknown'" class="notice" type="info" :closable="false" :title="posture.scheduler.liveness_reason_code || '当前没有持久化心跳事实，无法判断进程存活。'" />
      </el-card>
    </div>

    <el-card v-if="posture || diagnosticsError" shadow="never" class="diagnostics-card">
      <template #header><div class="card-title"><strong>Worker / Scheduler 诊断</strong><span class="muted">仅展示后端 Durable Facts，不推断进程心跳</span></div></template>
      <el-alert v-if="diagnosticsError" type="warning" :closable="false" title="诊断数据暂时不可用；全局运行态势仍可继续查看。" />
      <div class="diagnostics-grid">
        <section v-if="workerDiagnostics" class="diagnostics-section">
          <div class="section-title"><strong>Worker Claim / Lease</strong><el-tag :type="livenessType(workerDiagnostics.liveness)">{{ livenessLabel(workerDiagnostics.liveness) }}</el-tag></div>
          <div class="diagnostic-metrics"><div><span>Frontier 总量</span><strong>{{ workerDiagnostics.frontier.total }}</strong></div><div><span>活动 Lease</span><strong>{{ workerDiagnostics.leases.active }}</strong></div><div><span>过期 Lease</span><strong>{{ workerDiagnostics.leases.expired }}</strong></div><div><span>Worker Owner</span><strong>{{ workerDiagnostics.owners.length }}</strong></div></div>
          <el-table :data="workerDiagnostics.owners" size="small" empty-text="暂无 Worker Owner"><el-table-column prop="worker_owner" label="Worker Owner" min-width="220" show-overflow-tooltip /><el-table-column prop="claim_count" label="Claim 次数" width="100" /></el-table>
          <el-table :data="workerDiagnostics.recent_errors" size="small" empty-text="暂无最近错误" class="diagnostic-table"><el-table-column prop="execution_id" label="Execution ID" min-width="220" show-overflow-tooltip /><el-table-column prop="error_code" label="错误码" min-width="150" /><el-table-column prop="attempt" label="尝试" width="80" /><el-table-column prop="created_at" label="发生时间" min-width="180" /></el-table>
        </section>
        <section v-if="schedulerDiagnostics" class="diagnostics-section">
          <div class="section-title"><strong>Scheduler Durable</strong><el-tag :type="livenessType(schedulerDiagnostics.liveness)">{{ livenessLabel(schedulerDiagnostics.liveness) }}</el-tag></div>
          <div class="diagnostic-metrics"><div><span>启用 Schedule</span><strong>{{ schedulerDiagnostics.durable.enabled_scheduled_triggers }}</strong></div><div><span>停用 Schedule</span><strong>{{ schedulerDiagnostics.durable.disabled_scheduled_triggers }}</strong></div><div><span>待处理 Frontier</span><strong>{{ schedulerDiagnostics.durable.pending_frontier_items }}</strong></div><div><span>Schedule 明细</span><strong>{{ schedulerDiagnostics.triggers.length }}</strong></div></div>
          <el-table :data="schedulerDiagnostics.triggers" size="small" empty-text="暂无 Schedule Trigger"><el-table-column prop="name" label="名称" min-width="180" /><el-table-column prop="status" label="状态" width="100" /><el-table-column prop="workflow_id" label="Workflow ID" min-width="220" show-overflow-tooltip /><el-table-column prop="updated_at" label="更新时间" min-width="180" /></el-table>
        </section>
      </div>
    </el-card>

    <el-card v-if="posture" shadow="never" class="summary-card">
      <template #header><div class="card-title"><strong>Execution 状态</strong><span>窗口：最近 {{ posture.window_hours }} 小时</span></div></template>
      <div class="status-grid compact">
        <div v-for="item in executionStatuses" :key="item.key" class="status-item"><span>{{ item.label }}</span><strong>{{ posture.executions.status_counts[item.key] || 0 }}</strong></div>
      </div>
    </el-card>

    <el-card v-if="posture" shadow="never" class="summary-card">
      <template #header><div class="card-title"><strong>Workflow / Trigger</strong><span>当前租户范围</span></div></template>
      <div class="status-grid compact two">
        <div class="status-item"><span>Workflow 总量</span><strong>{{ posture.workflows.total }}</strong></div>
        <div class="status-item"><span>Trigger 总量</span><strong>{{ posture.triggers.total }}</strong></div>
        <div class="status-item"><span>启用 Schedule Trigger</span><strong>{{ posture.triggers.scheduled_enabled }}</strong></div>
        <div v-for="item in triggerStatuses" :key="item.key" class="status-item"><span>Trigger {{ item.label }}</span><strong>{{ posture.triggers.status_counts[item.key] || 0 }}</strong></div>
      </div>
    </el-card>

    <el-card v-if="posture" shadow="never" class="executions-card">
      <template #header><strong>最近 Execution</strong></template>
      <el-table :data="posture.executions.items" empty-text="当前窗口没有 Execution">
        <el-table-column prop="workflow_name" label="Workflow" min-width="180" />
        <el-table-column prop="id" label="Execution" min-width="260" show-overflow-tooltip />
        <el-table-column label="状态" width="110"><template #default="{ row }"><el-tag :type="statusType(row.status)">{{ row.status }}</el-tag></template></el-table-column>
        <el-table-column prop="current_node_id" label="当前节点" min-width="160" show-overflow-tooltip />
        <el-table-column prop="worker_owner" label="Worker Owner" min-width="160" show-overflow-tooltip />
        <el-table-column prop="error_code" label="错误码" min-width="140" />
        <el-table-column prop="created_at" label="创建时间" min-width="190" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { Refresh } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { runtimeDiagnosticsApi, type RuntimeSchedulerDiagnostics, type RuntimeWorkerDiagnostics } from "@/api/runtimeDiagnostics";
import { runtimeOperationsApi, type RuntimeGlobalPosture } from "@/api/runtimeOperations";

const windowHours = ref(24);
const loading = ref(false);
const error = ref(false);
const diagnosticsError = ref(false);
const posture = ref<RuntimeGlobalPosture>();
const workerDiagnostics = ref<RuntimeWorkerDiagnostics>();
const schedulerDiagnostics = ref<RuntimeSchedulerDiagnostics>();
const executionStatuses = [
  { key: "pending", label: "待执行" }, { key: "running", label: "运行中" },
  { key: "completed", label: "已完成" }, { key: "failed", label: "失败" }, { key: "cancelled", label: "已取消" },
];
const triggerStatuses = [{ key: "enabled", label: "启用" }, { key: "disabled", label: "停用" }];

function livenessLabel(value: string) { return value === "healthy" ? "健康" : value === "unhealthy" ? "异常" : "未知"; }
function livenessType(value: string) { return value === "healthy" ? "success" : value === "unhealthy" ? "danger" : "info"; }
function statusType(value: string) { return value === "completed" ? "success" : value === "failed" ? "danger" : value === "running" ? "warning" : "info"; }

async function loadPosture() {
  loading.value = true;
  error.value = false;
  try {
    posture.value = (await runtimeOperationsApi.global({ window_hours: windowHours.value, limit: 50 })).data;
  } catch {
    error.value = true;
    ElMessage.error("全局 Runtime 数据加载失败，请稍后重试");
  } finally {
    loading.value = false;
  }
}

async function loadDiagnostics() {
  diagnosticsError.value = false;
  const [worker, scheduler] = await Promise.allSettled([
    runtimeDiagnosticsApi.worker(windowHours.value, 50),
    runtimeDiagnosticsApi.scheduler(50),
  ]);
  if (worker.status === "fulfilled") workerDiagnostics.value = worker.value.data;
  else workerDiagnostics.value = undefined;
  if (scheduler.status === "fulfilled") schedulerDiagnostics.value = scheduler.value.data;
  else schedulerDiagnostics.value = undefined;
  diagnosticsError.value = worker.status === "rejected" || scheduler.status === "rejected";
}

async function reload() {
  await Promise.all([loadPosture(), loadDiagnostics()]);
}

onMounted(reload);
</script>

<style scoped>
.global-runtime-page { padding: 24px; display: flex; flex-direction: column; gap: 16px; }
.page-header { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; }
.page-header h2 { margin: 0 0 8px; }
.page-header p { margin: 0; color: var(--el-text-color-secondary); }
.header-actions { display: flex; gap: 10px; }
.metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }
.metric-grid .el-card { display: flex; flex-direction: column; gap: 8px; }
.metric-grid span, .metric-grid small { color: var(--el-text-color-secondary); }
.metric-grid strong { font-size: 28px; line-height: 1.2; }
.status-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.status-grid.compact { grid-template-columns: repeat(5, minmax(0, 1fr)); }
.status-grid.compact.two { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.card-title, .section-title { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.status-list { display: grid; gap: 14px; }
.status-list > div, .status-item { display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--el-border-color-lighter); }
.status-item { flex-direction: column; align-items: flex-start; gap: 6px; }
.status-item span, .muted, .diagnostic-metrics span { color: var(--el-text-color-secondary); }
.status-item strong { font-size: 22px; }
.notice { margin-top: 16px; }
.summary-card, .executions-card, .diagnostics-card { overflow: hidden; }
.diagnostics-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px; }
.diagnostics-section { min-width: 0; }
.diagnostic-metrics { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; margin: 14px 0; }
.diagnostic-metrics > div { padding: 10px; border: 1px solid var(--el-border-color-lighter); border-radius: 8px; }
.diagnostic-metrics span, .diagnostic-metrics strong { display: block; }
.diagnostic-metrics strong { margin-top: 4px; font-size: 18px; }
.diagnostic-table { margin-top: 12px; }
@media (max-width: 1100px) { .metric-grid, .status-grid.compact, .status-grid.compact.two, .diagnostic-metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); } .diagnostics-grid { grid-template-columns: 1fr; } }
@media (max-width: 720px) { .page-header { flex-direction: column; } .header-actions { width: 100%; } .header-actions :deep(.el-select) { flex: 1; } .metric-grid, .status-grid { grid-template-columns: 1fr; } .diagnostic-metrics { grid-template-columns: 1fr 1fr; } .global-runtime-page { padding: 16px; } }
</style>
