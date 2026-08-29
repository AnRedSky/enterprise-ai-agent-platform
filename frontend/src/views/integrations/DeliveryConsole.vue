<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh, View, RefreshRight, CircleCheck, Warning, Clock, CircleClose } from "@element-plus/icons-vue";
import { integrationApi, type WebhookDelivery, type WebhookDeliveryAudit } from "@/api/integrations";

const loading = ref(false);
const auditLoading = ref(false);
const deliveries = ref<WebhookDelivery[]>([]);
const auditItems = ref<WebhookDeliveryAudit[]>([]);
const status = ref("");
const auditDialog = ref(false);
const selectedDelivery = ref<WebhookDelivery | null>(null);

const statusOptions = [
  { value: "pending", label: "待投递" },
  { value: "delivering", label: "投递中" },
  { value: "delivered", label: "已送达" },
  { value: "retrying", label: "重试中" },
  { value: "dead_letter", label: "死信" },
  { value: "failed", label: "失败" },
];

const statusSummary = computed(() => ({
  total: deliveries.value.length,
  delivered: deliveries.value.filter((item) => item.status === "delivered").length,
  retrying: deliveries.value.filter((item) => item.status === "retrying").length,
  failed: deliveries.value.filter((item) => ["failed", "dead_letter"].includes(item.status)).length,
}));

function statusLabel(value: string) {
  return statusOptions.find((item) => item.value === value)?.label || value;
}

function statusType(value: string) {
  if (value === "delivered") return "success";
  if (["failed", "dead_letter"].includes(value)) return "danger";
  if (["retrying", "delivering"].includes(value)) return "warning";
  return "info";
}

function statusIcon(value: string) {
  if (value === "delivered") return CircleCheck;
  if (["failed", "dead_letter"].includes(value)) return CircleClose;
  if (value === "retrying") return RefreshRight;
  return Clock;
}

function formatTime(value: string | null) {
  if (!value) return "—";
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}

async function loadDeliveries() {
  loading.value = true;
  try {
    const response = await integrationApi.deliveries(status.value ? { status: status.value } : undefined);
    deliveries.value = response.data;
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "Delivery 数据加载失败");
  } finally {
    loading.value = false;
  }
}

async function openAudit(delivery: WebhookDelivery) {
  selectedDelivery.value = delivery;
  auditDialog.value = true;
  auditLoading.value = true;
  auditItems.value = [];
  try {
    const response = await integrationApi.deliveryAudit(delivery.id);
    auditItems.value = response.data;
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "Delivery Audit 加载失败");
  } finally {
    auditLoading.value = false;
  }
}

async function replay(delivery: WebhookDelivery) {
  try {
    await ElMessageBox.confirm(
      `确认重新投递该 Delivery？当前状态为“${statusLabel(delivery.status)}”，系统会重新进入可靠投递流程。`,
      "确认 Replay",
      { type: "warning", confirmButtonText: "重新投递", cancelButtonText: "取消" },
    );
    await integrationApi.replayDelivery(delivery.id);
    ElMessage.success("Replay 已提交");
    await loadDeliveries();
  } catch (error) {
    if (error === "cancel" || error === "close") return;
    ElMessage.error(error instanceof Error ? error.message : "Replay 失败");
  }
}

onMounted(loadDeliveries);
</script>

<template>
  <section class="delivery-console">
    <div class="delivery-summary">
      <div class="summary-item"><span>当前记录</span><strong>{{ statusSummary.total }}</strong></div>
      <div class="summary-item success"><span>已送达</span><strong>{{ statusSummary.delivered }}</strong></div>
      <div class="summary-item warning"><span>重试中</span><strong>{{ statusSummary.retrying }}</strong></div>
      <div class="summary-item danger"><span>失败 / 死信</span><strong>{{ statusSummary.failed }}</strong></div>
    </div>

    <div class="delivery-toolbar">
      <div><strong>Delivery Operations</strong><span>观察可靠投递状态、失败原因与审计轨迹，并对可恢复失败执行 Replay。</span></div>
      <div class="toolbar-actions">
        <el-select v-model="status" clearable placeholder="全部状态" style="width: 150px" @change="loadDeliveries">
          <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-button :icon="Refresh" :loading="loading" @click="loadDeliveries">刷新</el-button>
      </div>
    </div>

    <el-alert title="运维提示" description="Delivery 是 Durable Event 投递事实。Replay 只重新进入后端可靠投递流程，不在浏览器直接调用目标 Endpoint。" type="info" :closable="false" show-icon class="delivery-note" />

    <el-table v-loading="loading" :data="deliveries" empty-text="暂无 Delivery 记录" class="delivery-table">
      <el-table-column label="状态" width="130">
        <template #default="scope">
          <span class="delivery-status"><component :is="statusIcon(scope.row.status)" /><el-tag :type="statusType(scope.row.status)" effect="light">{{ statusLabel(scope.row.status) }}</el-tag></span>
        </template>
      </el-table-column>
      <el-table-column label="Delivery / Event" min-width="270">
        <template #default="scope"><div class="id-cell"><strong>{{ scope.row.id }}</strong><span>{{ scope.row.integration_event_id }}</span></div></template>
      </el-table-column>
      <el-table-column prop="attempt_count" label="尝试次数" width="100" />
      <el-table-column label="HTTP" width="90">
        <template #default="scope"><span :class="scope.row.response_status_code && scope.row.response_status_code >= 400 ? 'http-error' : ''">{{ scope.row.response_status_code ?? "—" }}</span></template>
      </el-table-column>
      <el-table-column label="最近错误" min-width="220" show-overflow-tooltip>
        <template #default="scope"><span class="error-cell">{{ scope.row.last_error_code || scope.row.last_error_message || "—" }}</span></template>
      </el-table-column>
      <el-table-column label="更新时间" width="175"><template #default="scope">{{ formatTime(scope.row.updated_at) }}</template></el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="scope">
          <el-button link type="primary" :icon="View" @click="openAudit(scope.row)">Audit</el-button>
          <el-button v-if="['failed', 'dead_letter'].includes(scope.row.status)" link type="warning" :icon="RefreshRight" @click="replay(scope.row)">Replay</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="auditDialog" title="Delivery Audit" width="760px">
      <div v-if="selectedDelivery" class="audit-header">
        <div><span>Delivery</span><strong>{{ selectedDelivery.id }}</strong></div>
        <div><span>状态</span><el-tag :type="statusType(selectedDelivery.status)">{{ statusLabel(selectedDelivery.status) }}</el-tag></div>
        <div><span>尝试次数</span><strong>{{ selectedDelivery.attempt_count }}</strong></div>
      </div>
      <el-timeline v-loading="auditLoading" class="audit-timeline">
        <el-timeline-item v-for="item in auditItems" :key="item.id" :timestamp="formatTime(item.created_at)" placement="top">
          <div class="audit-item"><div class="audit-title"><strong>{{ item.action }}</strong><el-tag size="small" :type="statusType(item.status)">{{ statusLabel(item.status) }}</el-tag></div><p>Actor：{{ item.actor }} · Attempt：{{ item.attempt_count }} · HTTP：{{ item.response_status_code ?? "—" }}</p><p v-if="item.error_code || item.error_message" class="audit-error">{{ item.error_code || "ERROR" }}：{{ item.error_message || "—" }}</p></div>
        </el-timeline-item>
        <el-empty v-if="!auditLoading && !auditItems.length" description="暂无 Audit 记录" />
      </el-timeline>
    </el-dialog>
  </section>
</template>

<style scoped>
.delivery-console{display:grid;gap:18px}.delivery-summary{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.summary-item{padding:14px 16px;border:1px solid #eaecf0;border-radius:10px;background:#f8fafc}.summary-item span{display:block;color:#667085;font-size:11px}.summary-item strong{display:block;margin-top:4px;color:#101828;font-size:21px}.summary-item.success strong{color:#2f855a}.summary-item.warning strong{color:#b7791f}.summary-item.danger strong{color:#c53030}.delivery-toolbar{display:flex;justify-content:space-between;align-items:center;gap:16px}.delivery-toolbar div:first-child{display:grid;gap:4px}.delivery-toolbar strong{color:#344054;font-size:14px}.delivery-toolbar span{color:#98a2b3;font-size:12px}.toolbar-actions{display:flex;align-items:center;gap:8px}.delivery-note{margin-bottom:0}.delivery-table{border:1px solid #eaecf0;border-radius:10px}.delivery-status{display:inline-flex;align-items:center;gap:6px}.delivery-status>svg{width:14px;height:14px}.id-cell{display:grid;gap:4px;min-width:0}.id-cell strong{overflow:hidden;text-overflow:ellipsis;color:#344054;font-size:12px}.id-cell span{overflow:hidden;text-overflow:ellipsis;color:#98a2b3;font-size:10px}.error-cell{color:#667085;font-size:12px}.http-error{color:#c53030;font-weight:600}.audit-header{display:grid;grid-template-columns:1fr 160px 100px;gap:16px;margin-bottom:18px;padding:14px;border:1px solid #eaecf0;border-radius:10px;background:#f8fafc}.audit-header div{display:grid;gap:5px}.audit-header span{color:#98a2b3;font-size:10px}.audit-header strong{color:#344054;font-size:12px}.audit-timeline{padding:4px 10px}.audit-item{padding:10px 12px;border:1px solid #eaecf0;border-radius:8px;background:#fff}.audit-title{display:flex;align-items:center;gap:8px}.audit-item p{margin:6px 0 0;color:#667085;font-size:11px}.audit-item .audit-error{color:#c53030}@media(max-width:900px){.delivery-summary{grid-template-columns:repeat(2,1fr)}.delivery-toolbar{align-items:stretch;flex-direction:column}.toolbar-actions{justify-content:flex-start}.audit-header{grid-template-columns:1fr 1fr}}@media(max-width:600px){.delivery-summary{grid-template-columns:1fr}.toolbar-actions{flex-wrap:wrap}}
</style>
