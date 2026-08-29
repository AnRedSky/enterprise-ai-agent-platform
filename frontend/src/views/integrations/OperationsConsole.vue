<template>
  <div class="operations-console">
    <div class="toolbar">
      <div>
        <strong>运行运维总览</strong>
        <span>统一观察 Integration Event、Delivery、SLO 与死信状态；所有数据严格限制在当前租户。</span>
      </div>
      <div class="toolbar-actions">
        <el-select v-model="windowHours" style="width: 120px" @change="loadOverview">
          <el-option label="最近 1 小时" :value="1" />
          <el-option label="最近 24 小时" :value="24" />
          <el-option label="最近 7 天" :value="168" />
        </el-select>
        <el-button :icon="Refresh" :loading="loading" @click="loadAll">刷新</el-button>
      </div>
    </div>

    <el-alert v-if="error" type="error" :closable="false" title="运维数据加载失败，请检查 Runtime API 与数据库连接。" show-icon />

    <div class="metric-grid" v-if="overview">
      <div class="metric-card"><span>事件总量</span><strong>{{ overview.events.total }}</strong><small>{{ statusCount(overview.events.status_counts, "delivered") }} 已送达</small></div>
      <div class="metric-card"><span>Delivery 总量</span><strong>{{ overview.deliveries.total }}</strong><small>{{ statusCount(overview.deliveries.status_counts, "pending") }} 待处理</small></div>
      <div class="metric-card danger"><span>死信</span><strong>{{ overview.deliveries.dead_letter_count }}</strong><small>{{ overview.deliveries.retry_count }} 次发生重试</small></div>
      <div class="metric-card"><span>投递成功率</span><strong>{{ overview.slo.delivery_success_percent.toFixed(2) }}%</strong><small>目标 {{ overview.slo.target_percent.toFixed(2) }}%</small></div>
    </div>

    <div class="slo-grid" v-if="overview">
      <el-card shadow="never">
        <template #header><div class="card-title"><strong>SLO</strong><el-tag :type="overview.slo.delivery_success_percent >= overview.slo.target_percent ? 'success' : 'danger'">{{ overview.slo.delivery_success_percent >= overview.slo.target_percent ? '达标' : '未达标' }}</el-tag></div></template>
        <div class="slo-row"><span>投递成功率</span><strong>{{ overview.slo.delivery_success_percent.toFixed(4) }}%</strong></div>
        <div class="slo-row"><span>错误预算剩余</span><strong>{{ overview.slo.error_budget_percent.toFixed(4) }}%</strong></div>
        <div class="slo-row"><span>P95 投递延迟</span><strong>{{ overview.slo.p95_delivery_latency_ms == null ? '-' : `${overview.slo.p95_delivery_latency_ms} ms` }}</strong></div>
        <el-progress :percentage="Math.min(100, overview.slo.delivery_success_percent)" :status="overview.slo.delivery_success_percent >= overview.slo.target_percent ? 'success' : 'exception'" :stroke-width="8" />
      </el-card>
      <el-card shadow="never">
        <template #header><strong>事件状态分布</strong></template>
        <div v-for="item in eventStatuses" :key="item.key" class="status-row"><span>{{ item.label }}</span><strong>{{ statusCount(overview.events.status_counts, item.key) }}</strong></div>
      </el-card>
      <el-card shadow="never">
        <template #header><strong>Delivery 状态分布</strong></template>
        <div v-for="item in deliveryStatuses" :key="item.key" class="status-row"><span>{{ item.label }}</span><strong>{{ statusCount(overview.deliveries.status_counts, item.key) }}</strong></div>
      </el-card>
    </div>

    <el-card shadow="never" class="dead-letter-card">
      <template #header>
        <div class="card-title"><div><strong>死信管理</strong><span>仅展示当前租户已进入 dead_letter 的 Delivery。</span></div><el-button link type="primary" @click="loadDeadLetters">刷新</el-button></div>
      </template>
      <el-table v-loading="deadLetterLoading" :data="deadLetters" empty-text="当前没有死信">
        <el-table-column prop="id" label="Delivery" min-width="270" show-overflow-tooltip />
        <el-table-column prop="integration_event_id" label="事件" min-width="270" show-overflow-tooltip />
        <el-table-column label="尝试次数" width="100"><template #default="{ row }">{{ row.attempt_count }}</template></el-table-column>
        <el-table-column label="HTTP" width="90"><template #default="{ row }">{{ row.response_status_code || '-' }}</template></el-table-column>
        <el-table-column label="错误" min-width="190" show-overflow-tooltip><template #default="{ row }">{{ row.last_error_code || row.last_error_message || '-' }}</template></el-table-column>
        <el-table-column label="更新时间" min-width="180"><template #default="{ row }">{{ formatTime(row.updated_at) }}</template></el-table-column>
        <el-table-column label="操作" width="100" fixed="right"><template #default="{ row }"><el-button link type="primary" :loading="replayingId === row.id" @click="replay(row.id)">重新投递</el-button></template></el-table-column>
      </el-table>
      <el-pagination v-if="deadLetterTotal" v-model:current-page="deadLetterPage" v-model:page-size="deadLetterPageSize" :total="deadLetterTotal" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @change="loadDeadLetters" />
    </el-card>

    <div class="navigation-note">
      <span>事件、Delivery 与不可变审计明细仍保留在对应运维页，当前总览只负责聚合指标与死信操作。</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import { request } from "@/api/request";
import { integrationApi, type WebhookDelivery } from "@/api/integrations";

interface OperationsOverview {
  window_hours: number;
  since: string;
  generated_at: string;
  events: { total: number; status_counts: Record<string, number> };
  deliveries: { total: number; status_counts: Record<string, number>; retry_count: number; dead_letter_count: number };
  slo: { target_percent: number; delivery_success_percent: number; error_budget_percent: number; p95_delivery_latency_ms: number | null };
}

interface DeadLetterResponse { items: WebhookDelivery[]; page: number; page_size: number; total: number }

const overview = ref<OperationsOverview>();
const deadLetters = ref<WebhookDelivery[]>([]);
const loading = ref(false);
const deadLetterLoading = ref(false);
const error = ref(false);
const windowHours = ref(24);
const deadLetterPage = ref(1);
const deadLetterPageSize = ref(20);
const deadLetterTotal = ref(0);
const replayingId = ref("");

const eventStatuses = [
  { key: "pending", label: "待处理" }, { key: "processing", label: "处理中" },
  { key: "delivered", label: "已送达" }, { key: "failed", label: "处理失败" }, { key: "dead_letter", label: "死信" },
];
const deliveryStatuses = [
  { key: "pending", label: "待处理" }, { key: "running", label: "执行中" },
  { key: "delivered", label: "已送达" }, { key: "failed", label: "失败" }, { key: "dead_letter", label: "死信" },
];

function statusCount(values: Record<string, number>, key: string) { return values[key] || 0; }
function formatTime(value: string) { const date = new Date(value); return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN", { hour12: false }); }

async function loadOverview() {
  loading.value = true; error.value = false;
  try { overview.value = (await request.get<OperationsOverview>("/runtime/operations/overview", { params: { window_hours: windowHours.value } })).data; }
  catch { error.value = true; ElMessage.error("运维指标加载失败"); }
  finally { loading.value = false; }
}

async function loadDeadLetters() {
  deadLetterLoading.value = true;
  try {
    const response = await request.get<DeadLetterResponse>("/runtime/operations/dead-letters", { params: { page: deadLetterPage.value, page_size: deadLetterPageSize.value } });
    deadLetters.value = response.data.items; deadLetterTotal.value = response.data.total;
  } catch { ElMessage.error("死信查询失败"); }
  finally { deadLetterLoading.value = false; }
}

async function loadAll() { await Promise.all([loadOverview(), loadDeadLetters()]); }

async function replay(deliveryId: string) {
  try {
    await ElMessageBox.confirm("重新投递会将该 Delivery 重新置为 pending，并由 Worker 后续领取，不会由浏览器直接发送请求。", "确认重新投递", { type: "warning" });
    replayingId.value = deliveryId;
    await integrationApi.replayDelivery(deliveryId);
    ElMessage.success("Delivery 已重新进入投递队列");
    await loadAll();
  } catch (error) {
    if (error !== "cancel" && error !== "close") ElMessage.error(error instanceof Error ? error.message : "重新投递失败");
  } finally { replayingId.value = ""; }
}

onMounted(loadAll);
</script>

<style scoped>
.operations-console{padding-top:4px}.toolbar{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:18px}.toolbar>div:first-child{display:grid;gap:4px}.toolbar strong{color:#344054;font-size:14px}.toolbar span{color:#98a2b3;font-size:12px}.toolbar-actions{display:flex;align-items:center;gap:8px}.metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:14px}.metric-card{padding:15px 16px;border:1px solid #eaecf0;border-radius:10px;background:#fff}.metric-card span,.metric-card small{display:block;color:#98a2b3;font-size:11px}.metric-card strong{display:block;margin:5px 0;color:#101828;font-size:24px}.metric-card.danger strong{color:#d92d20}.slo-grid{display:grid;grid-template-columns:1.3fr 1fr 1fr;gap:12px;margin-bottom:14px}.card-title{display:flex;align-items:center;justify-content:space-between;gap:12px}.card-title>div{display:grid;gap:4px}.card-title span{color:#98a2b3;font-size:11px;font-weight:400}.slo-row,.status-row{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #f2f4f7;color:#667085;font-size:12px}.slo-row strong,.status-row strong{color:#344054}.slo-row:last-of-type,.status-row:last-child{border-bottom:0}.dead-letter-card{margin-bottom:10px}.dead-letter-card :deep(.el-pagination){margin-top:16px}.navigation-note{padding:10px 12px;border:1px dashed #d0d5dd;border-radius:8px;color:#98a2b3;font-size:11px;background:#f8fafc}@media(max-width:1000px){.metric-grid{grid-template-columns:repeat(2,1fr)}.slo-grid{grid-template-columns:1fr}}@media(max-width:680px){.metric-grid{grid-template-columns:1fr}.toolbar{align-items:stretch;flex-direction:column}}
</style>
