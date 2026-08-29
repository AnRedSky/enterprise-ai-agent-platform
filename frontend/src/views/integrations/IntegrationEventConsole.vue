<template>
  <div class="event-console">
    <div class="toolbar">
      <div>
        <strong>Durable Integration Events</strong>
        <span>查看 Runtime、Workflow、Agent、Scheduler 产生的可靠事件事实。</span>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
    </div>

    <el-form inline @submit.prevent class="filters">
      <el-input v-model="filters.event_type" clearable placeholder="Event Type" @keyup.enter="applyFilters" />
      <el-input v-model="filters.source" clearable placeholder="Source" @keyup.enter="applyFilters" />
      <el-select v-model="filters.status" clearable placeholder="Status" style="width: 150px">
        <el-option label="Pending" value="pending" />
        <el-option label="Processing" value="processing" />
        <el-option label="Delivered" value="delivered" />
        <el-option label="Failed" value="failed" />
        <el-option label="Dead Letter" value="dead_letter" />
      </el-select>
      <el-input v-model="filters.subject" clearable placeholder="Subject" @keyup.enter="applyFilters" />
      <el-button type="primary" @click="applyFilters">查询</el-button>
    </el-form>

    <el-alert v-if="error" type="error" :closable="false" title="Integration Event 查询失败，请稍后重试" />
    <el-empty v-else-if="!loading && items.length === 0" description="暂无 Integration Event" />
    <el-table v-else :data="items" v-loading="loading" @row-click="open">
      <el-table-column label="Event Type" min-width="250">
        <template #default="{ row }"><strong>{{ row.event_type }}</strong></template>
      </el-table-column>
      <el-table-column prop="source" label="Source" width="130" />
      <el-table-column prop="subject" label="Subject" min-width="190" show-overflow-tooltip />
      <el-table-column label="Status" width="125">
        <template #default="{ row }"><el-tag :type="statusType(row.status)">{{ row.status }}</el-tag></template>
      </el-table-column>
      <el-table-column label="Attempts" width="95"><template #default="{ row }">{{ row.attempt_count }}</template></el-table-column>
      <el-table-column label="Occurred" min-width="185"><template #default="{ row }">{{ formatTime(row.occurred_at) }}</template></el-table-column>
      <el-table-column label="ID" width="120"><template #default="{ row }"><el-button link type="primary" @click.stop="copy(row.id)">复制 ID</el-button></template></el-table-column>
    </el-table>

    <el-pagination
      v-if="total"
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      :page-sizes="[10, 20, 50, 100]"
      layout="total, sizes, prev, pager, next"
      @change="load"
    />
  </div>

  <el-drawer v-model="drawer" title="Integration Event 详情" size="58%">
    <template v-if="selected">
      <div class="event-summary">
        <div><span>Event Type</span><strong>{{ selected.event_type }}</strong></div>
        <div><span>Status</span><el-tag :type="statusType(selected.status)">{{ selected.status }}</el-tag></div>
        <div><span>Source</span><strong>{{ selected.source }}</strong></div>
        <div><span>Schema</span><strong>v{{ selected.schema_version }}</strong></div>
      </div>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="Event ID"><el-button link type="primary" @click="copy(selected.id)">{{ selected.id }}</el-button></el-descriptions-item>
        <el-descriptions-item label="Subject">{{ selected.subject }}</el-descriptions-item>
        <el-descriptions-item label="Idempotency Key" :span="2">{{ selected.idempotency_key }}</el-descriptions-item>
        <el-descriptions-item label="Trace ID">{{ selected.trace_id || "-" }}</el-descriptions-item>
        <el-descriptions-item label="Request ID">{{ selected.request_id || "-" }}</el-descriptions-item>
        <el-descriptions-item label="Occurred At">{{ formatTime(selected.occurred_at) }}</el-descriptions-item>
        <el-descriptions-item label="Created At">{{ formatTime(selected.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="Attempts">{{ selected.attempt_count }}</el-descriptions-item>
        <el-descriptions-item label="Last Error">{{ selected.last_error_code || "-" }}</el-descriptions-item>
      </el-descriptions>
      <el-divider>Payload</el-divider>
      <pre class="json-block">{{ JSON.stringify(selected.payload, null, 2) }}</pre>
      <el-divider v-if="Object.keys(selected.metadata_json).length">Metadata</el-divider>
      <pre v-if="Object.keys(selected.metadata_json).length" class="json-block">{{ JSON.stringify(selected.metadata_json, null, 2) }}</pre>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import { integrationApi, type IntegrationEvent } from "@/api/integrations";

const items = ref<IntegrationEvent[]>([]);
const selected = ref<IntegrationEvent>();
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const loading = ref(false);
const error = ref(false);
const drawer = ref(false);
const filters = reactive({ event_type: "", source: "", status: "", subject: "" });

function params() {
  return {
    page: page.value,
    page_size: pageSize.value,
    ...(filters.event_type ? { event_type: filters.event_type } : {}),
    ...(filters.source ? { source: filters.source } : {}),
    ...(filters.status ? { status: filters.status } : {}),
    ...(filters.subject ? { subject: filters.subject } : {}),
  };
}

async function load() {
  loading.value = true;
  error.value = false;
  try {
    const response = await integrationApi.integrationEvents(params());
    items.value = response.data.items;
    total.value = response.data.total;
  } catch {
    error.value = true;
    ElMessage.error("Integration Event 查询失败");
  } finally {
    loading.value = false;
  }
}

function applyFilters() {
  page.value = 1;
  void load();
}

function open(row: IntegrationEvent) {
  selected.value = row;
  drawer.value = true;
}

function formatTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}

function statusType(status: string) {
  if (status === "delivered") return "success";
  if (status === "failed" || status === "dead_letter") return "danger";
  if (status === "processing") return "warning";
  return "info";
}

async function copy(value: string) {
  try {
    await navigator.clipboard.writeText(value);
    ElMessage.success("ID 已复制");
  } catch {
    ElMessage.error("复制失败，请手动复制");
  }
}

onMounted(load);
</script>

<style scoped>
.event-console{padding-top:4px}.toolbar{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:16px}.toolbar div{display:grid;gap:4px}.toolbar strong{color:#344054;font-size:14px}.toolbar span{color:#98a2b3;font-size:12px}.filters{margin-bottom:16px}.filters :deep(.el-input){width:190px}.event-summary{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:18px}.event-summary>div{display:grid;gap:5px;padding:12px;border:1px solid #eaecf0;border-radius:8px}.event-summary span{color:#98a2b3;font-size:11px}.event-summary strong{color:#344054;font-size:13px;word-break:break-all}.json-block{max-height:300px;overflow:auto;margin:0;padding:14px;border:1px solid #eaecf0;border-radius:8px;background:#f8fafc;font-size:12px;line-height:1.55;white-space:pre-wrap;word-break:break-word}@media(max-width:900px){.event-summary{grid-template-columns:repeat(2,1fr)}}
</style>
