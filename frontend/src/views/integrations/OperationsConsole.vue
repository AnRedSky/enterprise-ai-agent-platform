<template>
  <div class="operations-console">
    <div class="toolbar">
      <div>
        <strong>Runtime 企业运维中心</strong>
        <span>统一观察全局运行态势与 Event、Delivery、SLO、Provider、Alert、Metrics、Audit 和死信；数据严格限制在当前租户。</span>
      </div>
      <div class="toolbar-actions">
        <el-select v-model="windowHours" style="width: 120px" @change="loadAll">
          <el-option label="最近 1 小时" :value="1" />
          <el-option label="最近 24 小时" :value="24" />
          <el-option label="最近 7 天" :value="168" />
        </el-select>
        <el-button :icon="Refresh" :loading="loading" @click="loadAll">刷新</el-button>
      </div>
    </div>
    <el-alert v-if="error" type="error" :closable="false" title="Runtime 运维数据加载失败，请稍后刷新重试。" show-icon />

    <el-tabs v-model="activeTab" class="operations-tabs">
      <el-tab-pane label="全局运行态势" name="global">
        <div v-if="globalPosture" class="metric-grid">
          <div class="metric-card"><span>执行总量</span><strong>{{ globalPosture.executions.total }}</strong><small>{{ globalPosture.executions.active_count }} 个执行中</small></div>
          <div class="metric-card"><span>工作流</span><strong>{{ globalPosture.workflows.total }}</strong><small>{{ globalPosture.workflows.status_counts.active || 0 }} 个活跃</small></div>
          <div class="metric-card"><span>调度积压</span><strong>{{ globalPosture.scheduler.durable_frontier_backlog }}</strong><small>{{ globalPosture.scheduler.enabled_scheduled_triggers }} 个定时触发器已启用</small></div>
          <div class="metric-card"><span>Worker 租约</span><strong>{{ globalPosture.worker.leased_frontiers }}</strong><small>{{ globalPosture.worker.active_worker_owners }} 个活跃 Worker</small></div>
        </div>
        <div v-if="globalPosture" class="slo-grid">
          <el-card shadow="never">
            <template #header><div class="card-title"><strong>Worker 状态</strong><el-tag type="info">{{ livenessLabel(globalPosture.worker.liveness) }}</el-tag></div></template>
            <div class="status-row"><span>运行中 Frontier</span><strong>{{ globalPosture.worker.running_frontiers }}</strong></div>
            <div class="status-row"><span>待处理 Frontier</span><strong>{{ globalPosture.worker.pending_frontiers }}</strong></div>
            <div class="status-row"><span>过期租约</span><strong>{{ globalPosture.worker.expired_leases }}</strong></div>
            <small class="muted">{{ globalPosture.worker.liveness_reason_code }}</small>
          </el-card>
          <el-card shadow="never">
            <template #header><div class="card-title"><strong>Scheduler 状态</strong><el-tag type="info">{{ livenessLabel(globalPosture.scheduler.liveness) }}</el-tag></div></template>
            <div class="status-row"><span>已启用定时触发器</span><strong>{{ globalPosture.scheduler.enabled_scheduled_triggers }}</strong></div>
            <div class="status-row"><span>持久化 Frontier 积压</span><strong>{{ globalPosture.scheduler.durable_frontier_backlog }}</strong></div>
            <small class="muted">{{ globalPosture.scheduler.liveness_reason_code }}</small>
          </el-card>
          <el-card shadow="never">
            <template #header><strong>执行状态</strong></template>
            <div v-for="item in executionStatuses" :key="item.key" class="status-row"><span>{{ item.label }}</span><strong>{{ statusCount(globalPosture.executions.status_counts, item.key) }}</strong></div>
          </el-card>
        </div>
        <el-card v-if="globalPosture" shadow="never" class="recent-card">
          <template #header><div class="card-title"><strong>最近执行</strong><span class="muted">{{ globalPosture.window_hours }} 小时窗口</span></div></template>
          <el-table :data="globalPosture.executions.items" empty-text="当前窗口没有执行记录">
            <el-table-column prop="workflow_name" label="工作流" min-width="180" />
            <el-table-column prop="id" label="Execution ID" min-width="250" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="110" />
            <el-table-column prop="current_node_id" label="当前节点" min-width="150" show-overflow-tooltip />
            <el-table-column prop="worker_owner" label="Worker" min-width="150" show-overflow-tooltip />
            <el-table-column prop="created_at" label="创建时间" min-width="180" />
          </el-table>
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="总览" name="overview">
        <div v-if="overview" class="metric-grid">
          <div class="metric-card"><span>事件总量</span><strong>{{ overview.events.total }}</strong><small>{{ statusCount(overview.events.status_counts, "delivered") }} 已送达</small></div>
          <div class="metric-card"><span>Delivery 总量</span><strong>{{ overview.deliveries.total }}</strong><small>{{ statusCount(overview.deliveries.status_counts, "pending") }} 待处理</small></div>
          <div class="metric-card danger"><span>死信</span><strong>{{ overview.deliveries.dead_letter_count }}</strong><small>{{ overview.deliveries.retry_count }} 次发生重试</small></div>
          <div class="metric-card"><span>投递成功率</span><strong>{{ overview.slo.delivery_success_percent.toFixed(2) }}%</strong><small>目标 {{ overview.slo.target_percent.toFixed(2) }}%</small></div>
        </div>
        <div v-if="overview" class="slo-grid">
          <el-card shadow="never"><template #header><div class="card-title"><strong>SLO</strong><el-tag :type="sloHealthy ? 'success' : 'danger'">{{ sloHealthy ? '达标' : '未达标' }}</el-tag></div></template><div class="slo-row"><span>投递成功率</span><strong>{{ overview.slo.delivery_success_percent.toFixed(4) }}%</strong></div><div class="slo-row"><span>错误预算剩余</span><strong>{{ overview.slo.error_budget_percent.toFixed(4) }}%</strong></div><div class="slo-row"><span>P95 投递延迟</span><strong>{{ overview.slo.p95_delivery_latency_ms == null ? '-' : `${overview.slo.p95_delivery_latency_ms} ms` }}</strong></div><el-progress :percentage="Math.min(100, overview.slo.delivery_success_percent)" :status="sloHealthy ? 'success' : 'exception'" :stroke-width="8" /></el-card>
          <el-card shadow="never"><template #header><strong>事件状态</strong></template><div v-for="item in eventStatuses" :key="item.key" class="status-row"><span>{{ item.label }}</span><strong>{{ statusCount(overview.events.status_counts, item.key) }}</strong></div></el-card>
          <el-card shadow="never"><template #header><strong>Delivery 状态</strong></template><div v-for="item in deliveryStatuses" :key="item.key" class="status-row"><span>{{ item.label }}</span><strong>{{ statusCount(overview.deliveries.status_counts, item.key) }}</strong></div></el-card>
        </div>
      </el-tab-pane>

      <el-tab-pane label="告警" name="alerts">
        <div class="tab-toolbar"><div><strong>Alert 生命周期</strong><span>查看 firing / recovery，并可显式触发当前租户规则评估。</span></div><el-button type="primary" :loading="actionLoading" @click="evaluateAlerts">立即评估</el-button></div>
        <el-alert v-if="alertEvaluationMessage" :title="alertEvaluationMessage" type="success" :closable="false" class="inline-alert" />
        <el-table :data="alerts" v-loading="loadingAlerts" empty-text="暂无告警实例"><el-table-column prop="name" label="告警" min-width="180" /><el-table-column prop="severity" label="级别" width="100" /><el-table-column prop="status" label="状态" width="120" /><el-table-column prop="fired_at" label="触发时间" min-width="180" /><el-table-column prop="recovered_at" label="恢复时间" min-width="180" /></el-table>
        <el-divider>告警规则</el-divider>
        <el-table :data="alertRules" empty-text="暂无告警规则"><el-table-column prop="name" label="名称" min-width="180" /><el-table-column prop="metric_name" label="指标" min-width="180" /><el-table-column prop="operator" label="条件" width="90" /><el-table-column prop="threshold" label="阈值" width="100" /><el-table-column prop="window_minutes" label="窗口" width="90" /><el-table-column prop="severity" label="级别" width="100" /><el-table-column label="启用" width="100"><template #default="{ row }"><el-switch v-model="row.enabled" :loading="row.id === togglingRuleId" @change="toggleRule(row as RuntimeAlertRule)" /></template></el-table-column></el-table>
      </el-tab-pane>

      <el-tab-pane label="Provider" name="providers">
        <div class="tab-toolbar"><div><strong>通知 Provider</strong><span>管理租户级 Provider 元数据与健康状态；页面不会读取或展示 Secret。</span></div></div>
        <el-table :data="providers" v-loading="loadingProviders" empty-text="暂无 Provider"><el-table-column prop="name" label="名称" min-width="180" /><el-table-column prop="provider_type" label="类型" width="140" /><el-table-column label="状态" width="120"><template #default="{ row }"><el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '已启用' : '已停用' }}</el-tag></template></el-table-column><el-table-column prop="status" label="健康状态" width="120" /><el-table-column prop="last_checked_at" label="最近探测" min-width="180" /><el-table-column label="操作" width="190"><template #default="{ row }"><el-switch v-model="row.enabled" :loading="row.id === togglingProviderId" @change="toggleProvider(row as RuntimeProvider)" /><el-button link type="primary" :loading="row.id === probingProviderId" @click="probeProvider(row as RuntimeProvider)">健康探测</el-button></template></el-table-column></el-table>
        <el-alert v-if="providerMessage" :title="providerMessage" type="info" :closable="false" class="inline-alert" />
      </el-tab-pane>

      <el-tab-pane label="Metrics" name="metrics">
        <div class="tab-toolbar"><div><strong>Runtime 时间序列</strong><span>指标查询遵循后端 canonical metric / dimension Contract。</span></div><el-button :loading="metricLoading" @click="snapshotMetrics">采样快照</el-button></div>
        <el-form inline @submit.prevent="loadMetrics"><el-input v-model="metricName" placeholder="指标名称，例如 runtime.notification.delivery" clearable style="width: 280px" /><el-input-number v-model="metricWindow" :min="1" :max="10080" controls-position="right" /><el-input v-model="dimensionKey" placeholder="维度键（可选）" clearable style="width: 150px" /><el-input v-model="dimensionValue" placeholder="维度值（可选）" clearable style="width: 180px" /><el-button type="primary" @click="loadMetrics">查询</el-button></el-form>
        <el-table :data="metricSeries" v-loading="metricLoading" empty-text="暂无指标样本"><el-table-column prop="timestamp" label="时间" min-width="180" /><el-table-column prop="metric_name" label="指标" min-width="220" /><el-table-column prop="value" label="值" width="120" /><el-table-column prop="dimension_key" label="维度键" width="140" /><el-table-column prop="dimension_value" label="维度值" min-width="180" /></el-table>
      </el-tab-pane>

      <el-tab-pane label="Audit" name="audit">
        <div class="tab-toolbar"><div><strong>Runtime 运维审计</strong><span>支持分页、动作/资源/结果过滤和时间窗口查询；查询严格限制在当前租户。</span></div><el-button @click="loadAudit">刷新</el-button></div>
        <el-form inline class="audit-filters" @submit.prevent="queryAudit">
          <el-input v-model="auditAction" placeholder="动作（可选）" clearable style="width: 220px" />
          <el-input v-model="auditResourceType" placeholder="资源类型（可选）" clearable style="width: 160px" />
          <el-input v-model="auditResourceId" placeholder="资源标识（可选）" clearable style="width: 220px" />
          <el-select v-model="auditOutcome" placeholder="结果" clearable style="width: 130px">
            <el-option label="成功" value="success" />
            <el-option label="拒绝" value="rejected" />
            <el-option label="失败" value="failed" />
          </el-select>
          <el-input v-model="auditSince" type="datetime-local" aria-label="开始时间" style="width: 190px" />
          <el-input v-model="auditUntil" type="datetime-local" aria-label="结束时间" style="width: 190px" />
          <el-button type="primary" :loading="auditLoading" native-type="submit">查询</el-button>
          <el-button :disabled="auditLoading" @click="resetAuditFilters">重置</el-button>
        </el-form>
        <el-table :data="audits" v-loading="auditLoading" empty-text="暂无符合条件的运维审计">
          <el-table-column prop="action" label="操作" min-width="220" />
          <el-table-column prop="resource_type" label="资源类型" width="150" />
          <el-table-column prop="resource_id" label="资源标识" min-width="220" show-overflow-tooltip />
          <el-table-column prop="outcome" label="结果" width="110" />
          <el-table-column prop="actor_id" label="操作人" min-width="220" show-overflow-tooltip />
          <el-table-column prop="created_at" label="时间" min-width="180" />
        </el-table>
        <el-pagination v-if="auditTotal" v-model:current-page="auditPage" v-model:page-size="auditPageSize" :total="auditTotal" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" @change="loadAudit" />
      </el-tab-pane>

      <el-tab-pane label="死信" name="dead-letters">
        <div class="tab-toolbar"><div><strong>死信管理</strong><span>仅展示当前租户已进入 dead_letter 的 Delivery；重新投递只重新进入后端队列。</span></div><el-button link type="primary" @click="loadDeadLetters">刷新</el-button></div>
        <el-table v-loading="deadLetterLoading" :data="deadLetters" empty-text="当前没有死信"><el-table-column prop="id" label="Delivery" min-width="270" show-overflow-tooltip /><el-table-column prop="integration_event_id" label="事件" min-width="270" show-overflow-tooltip /><el-table-column prop="attempt_count" label="尝试次数" width="100" /><el-table-column prop="response_status_code" label="HTTP" width="90" /><el-table-column label="错误" min-width="190" show-overflow-tooltip><template #default="{ row }">{{ row.last_error_code || row.last_error_message || '-' }}</template></el-table-column><el-table-column prop="updated_at" label="更新时间" min-width="180" /><el-table-column label="操作" width="100" fixed="right"><template #default="{ row }"><el-button link type="primary" :loading="replayingId === row.id" @click="replay(row.id)">重新投递</el-button></template></el-table-column></el-table>
        <el-pagination v-if="deadLetterTotal" v-model:current-page="deadLetterPage" v-model:page-size="deadLetterPageSize" :total="deadLetterTotal" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @change="loadDeadLetters" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import { runtimeOperationsApi, type RuntimeAlert, type RuntimeAlertRule, type RuntimeDeadLetter, type RuntimeGlobalPosture, type RuntimeMetricSample, type RuntimeOperationsOverview, type RuntimeProvider } from "@/api/runtimeOperations";

const activeTab = ref("global");
const windowHours = ref(24);
const globalPosture = ref<RuntimeGlobalPosture>();
const overview = ref<RuntimeOperationsOverview>();
const alerts = ref<RuntimeAlert[]>([]);
const providers = ref<RuntimeProvider[]>([]);
const alertRules = ref<RuntimeAlertRule[]>([]);
const audits = ref<Record<string, unknown>[]>([]);
const metricSeries = ref<RuntimeMetricSample[]>([]);
const deadLetters = ref<RuntimeDeadLetter[]>([]);
const loading = ref(false);
const error = ref(false);
const loadingAlerts = ref(false);
const loadingProviders = ref(false);
const auditLoading = ref(false);
const metricLoading = ref(false);
const deadLetterLoading = ref(false);
const actionLoading = ref(false);
const deadLetterPage = ref(1);
const deadLetterPageSize = ref(20);
const deadLetterTotal = ref(0);
const auditPage = ref(1);
const auditPageSize = ref(20);
const auditTotal = ref(0);
const auditAction = ref("");
const auditResourceType = ref("");
const auditResourceId = ref("");
const auditOutcome = ref("");
const auditSince = ref("");
const auditUntil = ref("");
const replayingId = ref("");
const togglingProviderId = ref("");
const probingProviderId = ref("");
const togglingRuleId = ref("");
const alertEvaluationMessage = ref("");
const providerMessage = ref("");
const metricName = ref("runtime.notification.delivery");
const metricWindow = ref(60);
const dimensionKey = ref("");
const dimensionValue = ref("");
const executionStatuses = [{ key: "pending", label: "待处理" }, { key: "running", label: "运行中" }, { key: "completed", label: "已完成" }, { key: "failed", label: "失败" }, { key: "cancelled", label: "已取消" }];
const eventStatuses = [{ key: "pending", label: "待处理" }, { key: "processing", label: "处理中" }, { key: "delivered", label: "已送达" }, { key: "failed", label: "处理失败" }, { key: "dead_letter", label: "死信" }];
const deliveryStatuses = [{ key: "pending", label: "待处理" }, { key: "running", label: "执行中" }, { key: "delivered", label: "已送达" }, { key: "failed", label: "失败" }, { key: "dead_letter", label: "死信" }];
const sloHealthy = computed(() => !!overview.value && overview.value.slo.delivery_success_percent >= overview.value.slo.target_percent);
function statusCount(values: Record<string, number>, key: string) { return values[key] || 0; }
function livenessLabel(value: string) { return value === "unknown" ? "未知（无持久化心跳）" : value; }

async function loadGlobal() { globalPosture.value = (await runtimeOperationsApi.global({ window_hours: windowHours.value, limit: 50 })).data; }
async function loadOverview() { overview.value = (await runtimeOperationsApi.overview(windowHours.value)).data; }
async function loadAlerts() { loadingAlerts.value = true; try { alerts.value = (await runtimeOperationsApi.alerts(windowHours.value)).data.items; alertRules.value = (await runtimeOperationsApi.alertRules()).data.items; } finally { loadingAlerts.value = false; } }
async function loadProviders() { loadingProviders.value = true; try { providers.value = (await runtimeOperationsApi.providers()).data.items; } finally { loadingProviders.value = false; } }
function auditQueryParams() { return { page: auditPage.value, page_size: auditPageSize.value, action: auditAction.value.trim() || undefined, resource_type: auditResourceType.value.trim() || undefined, resource_id: auditResourceId.value.trim() || undefined, outcome: auditOutcome.value || undefined, since: auditSince.value || undefined, until: auditUntil.value || undefined }; }
async function loadAudit() { auditLoading.value = true; try { const result = await runtimeOperationsApi.auditQuery(auditQueryParams()); audits.value = result.data.items; auditTotal.value = result.data.total; } catch { ElMessage.error("审计查询失败，请检查筛选条件后重试。"); } finally { auditLoading.value = false; } }
async function queryAudit() { auditPage.value = 1; await loadAudit(); }
async function resetAuditFilters() { auditAction.value = ""; auditResourceType.value = ""; auditResourceId.value = ""; auditOutcome.value = ""; auditSince.value = ""; auditUntil.value = ""; auditPage.value = 1; await loadAudit(); }
async function loadMetrics() { metricLoading.value = true; try { metricSeries.value = (await runtimeOperationsApi.metricSeries(metricName.value.trim(), metricWindow.value, dimensionKey.value || undefined, dimensionValue.value || undefined)).data.items; } catch { ElMessage.error("指标查询失败，请稍后重试。"); } finally { metricLoading.value = false; } }
async function loadDeadLetters() { deadLetterLoading.value = true; try { const response = await runtimeOperationsApi.deadLetters(deadLetterPage.value, deadLetterPageSize.value); deadLetters.value = response.data.items; deadLetterTotal.value = response.data.total; } catch { ElMessage.error("死信查询失败，请稍后重试。"); } finally { deadLetterLoading.value = false; } }
async function loadAll() { loading.value = true; error.value = false; try { await Promise.all([loadGlobal(), loadOverview(), loadAlerts(), loadProviders(), loadAudit(), loadDeadLetters()]); } catch { error.value = true; } finally { loading.value = false; } }
async function evaluateAlerts() { actionLoading.value = true; try { const result = await runtimeOperationsApi.evaluateAlertRules(); alertEvaluationMessage.value = `规则评估完成，本次状态发生变化 ${result.data.count} 条`; await loadAlerts(); } catch { ElMessage.error("告警评估失败，请稍后重试。"); } finally { actionLoading.value = false; } }
async function toggleProvider(row: RuntimeProvider) { togglingProviderId.value = row.id; try { const result = await runtimeOperationsApi.setProviderEnabled(row.id, row.enabled); Object.assign(row, result.data); ElMessage.success(row.enabled ? "Provider 已启用" : "Provider 已停用"); } catch { row.enabled = !row.enabled; ElMessage.error("Provider 状态更新失败，请稍后重试。"); } finally { togglingProviderId.value = ""; } }
async function probeProvider(row: RuntimeProvider) { probingProviderId.value = row.id; try { const result = await runtimeOperationsApi.probeProviderHealth(row.id); row.status = result.data.status; row.last_checked_at = new Date().toISOString(); providerMessage.value = result.data.error ? `Provider ${row.name} 探测失败，请检查 Provider 配置。` : `Provider ${row.name} 探测完成：${result.data.status}${result.data.latency_ms == null ? "" : `，${result.data.latency_ms} ms`}`; } catch { ElMessage.error("Provider 健康探测失败，请稍后重试。"); } finally { probingProviderId.value = ""; } }
async function toggleRule(row: RuntimeAlertRule) { togglingRuleId.value = row.id; try { const result = await runtimeOperationsApi.setAlertRuleEnabled(row.id, row.enabled); Object.assign(row, result.data); ElMessage.success(row.enabled ? "告警规则已启用" : "告警规则已停用"); } catch { row.enabled = !row.enabled; ElMessage.error("告警规则状态更新失败，请稍后重试。"); } finally { togglingRuleId.value = ""; } }
async function snapshotMetrics() { try { const result = await runtimeOperationsApi.createMetricsSnapshot(); ElMessage.success(`已写入 ${result.data.samples_written} 条指标样本`); await loadMetrics(); } catch { ElMessage.error("指标采样失败，请稍后重试。"); } }
async function replay(deliveryId: string) { try { await ElMessageBox.confirm("重新投递会将 Delivery 重新进入后端队列，不会由浏览器直接请求目标地址。", "确认重新投递", { type: "warning" }); replayingId.value = deliveryId; const result = await runtimeOperationsApi.replayDeadLetters([deliveryId]); if (result.data.rejected.length) throw new Error(result.data.rejected[0].reason); ElMessage.success("Delivery 已重新进入投递队列"); await loadDeadLetters(); } catch (error) { if (error !== "cancel" && error !== "close") ElMessage.error("重新投递失败，请稍后重试。"); } finally { replayingId.value = ""; } }
onMounted(loadAll);
</script>

<style scoped>
.operations-console{padding:24px}.toolbar{display:flex;justify-content:space-between;gap:20px;margin-bottom:18px}.toolbar strong,.toolbar span{display:block}.toolbar span{margin-top:5px;color:#667085;font-size:12px}.toolbar-actions{display:flex;gap:10px}.metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.metric-card{padding:16px;border:1px solid #eaecf0;border-radius:10px}.metric-card span,.metric-card small,.muted{display:block;color:#667085;font-size:11px}.metric-card strong{display:block;margin:6px 0;font-size:24px;color:#101828}.metric-card.danger{border-color:#fecdca}.slo-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:14px}.card-title,.slo-row,.status-row{display:flex;justify-content:space-between;align-items:center}.slo-row,.status-row{margin:10px 0}.slo-row span,.status-row span{color:#667085;font-size:12px}.tab-toolbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}.tab-toolbar strong,.tab-toolbar span{display:block}.tab-toolbar span{margin-top:4px;color:#667085;font-size:12px}.audit-filters{margin-bottom:14px}.inline-alert{margin:10px 0}.recent-card{margin-top:14px}
@media(max-width:900px){.operations-console{padding:14px}.toolbar,.tab-toolbar{align-items:flex-start;flex-direction:column}.metric-grid,.slo-grid{grid-template-columns:1fr}.toolbar-actions{width:100%}.toolbar-actions :deep(.el-select){flex:1}.audit-filters :deep(.el-form-item){margin-right:0;width:100%}.audit-filters :deep(.el-input),.audit-filters :deep(.el-select){width:100%!important}}
</style>
