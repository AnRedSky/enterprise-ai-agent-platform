<template>
  <div class="event-console">
    <div class="toolbar">
      <div><strong>事件记录</strong><span>查看平台产生的可靠事件记录，了解事件来源、状态和关联信息。</span></div>
      <el-button :icon="Refresh" :loading="loading" @click="load">刷新</el-button>
    </div>

    <el-form inline @submit.prevent class="filters">
      <el-input v-model="filters.event_type" clearable placeholder="事件类型" @keyup.enter="applyFilters" />
      <el-input v-model="filters.source" clearable placeholder="来源" @keyup.enter="applyFilters" />
      <el-select v-model="filters.status" clearable placeholder="状态" style="width:150px"><el-option label="待处理" value="pending" /><el-option label="处理中" value="processing" /><el-option label="已送达" value="delivered" /><el-option label="处理失败" value="failed" /><el-option label="进入死信" value="dead_letter" /></el-select>
      <el-input v-model="filters.subject" clearable placeholder="关联对象" @keyup.enter="applyFilters" />
      <el-button type="primary" @click="applyFilters">查询</el-button>
    </el-form>

    <StatePanel v-if="loading" state="loading" title="正在加载事件记录" description="正在读取可靠事件记录，请稍候。" />
    <StatePanel v-else-if="error" state="error" title="事件记录查询失败" description="无法读取当前租户的事件记录，请稍后重试。" action-label="重新加载" @action="load" />
    <StatePanel v-else-if="items.length === 0" state="empty" title="暂无事件记录" description="当前筛选条件下没有可靠事件记录，可调整筛选条件后重试。" />
    <el-table v-else :data="items" row-key="id" @row-click="open">
      <el-table-column label="事件类型" min-width="250"><template #default="{ row }"><strong>{{ row.event_type }}</strong></template></el-table-column>
      <el-table-column prop="source" label="来源" width="130" />
      <el-table-column prop="subject" label="关联对象" min-width="190" show-overflow-tooltip />
      <el-table-column label="状态" width="125"><template #default="{ row }"><el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag></template></el-table-column>
      <el-table-column label="处理次数" width="95"><template #default="{ row }">{{ row.attempt_count }}</template></el-table-column>
      <el-table-column label="发生时间" min-width="185"><template #default="{ row }">{{ formatTime(row.occurred_at) }}</template></el-table-column>
      <el-table-column label="事件编号" width="120"><template #default="{ row }"><el-button link type="primary" @click.stop="copy(row.id)">复制编号</el-button></template></el-table-column>
    </el-table>

    <el-pagination v-if="total" v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10,20,50,100]" layout="total, sizes, prev, pager, next" @change="load" />
  </div>

  <el-drawer v-model="drawer" title="事件详情" size="58%">
    <template v-if="selected">
      <div class="event-summary"><div><span>事件类型</span><strong>{{ selected.event_type }}</strong></div><div><span>状态</span><el-tag :type="statusType(selected.status)">{{ statusLabel(selected.status) }}</el-tag></div><div><span>来源</span><strong>{{ selected.source }}</strong></div><div><span>数据版本</span><strong>v{{ selected.schema_version }}</strong></div></div>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="事件编号"><el-button link type="primary" @click="copy(selected.id)">{{ selected.id }}</el-button></el-descriptions-item>
        <el-descriptions-item label="关联对象">{{ selected.subject }}</el-descriptions-item>
        <el-descriptions-item label="幂等标识" :span="2">{{ selected.idempotency_key }}</el-descriptions-item>
        <el-descriptions-item label="链路追踪 ID">{{ selected.trace_id || "-" }}</el-descriptions-item><el-descriptions-item label="请求 ID">{{ selected.request_id || "-" }}</el-descriptions-item>
        <el-descriptions-item label="发生时间">{{ formatTime(selected.occurred_at) }}</el-descriptions-item><el-descriptions-item label="创建时间">{{ formatTime(selected.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="处理次数">{{ selected.attempt_count }}</el-descriptions-item><el-descriptions-item label="最近错误">{{ selected.last_error_code || "-" }}</el-descriptions-item>
      </el-descriptions>
      <el-divider>事件内容</el-divider><pre class="json-block">{{ JSON.stringify(selected.payload, null, 2) }}</pre>
      <el-divider v-if="Object.keys(selected.metadata_json).length">附加信息</el-divider><pre v-if="Object.keys(selected.metadata_json).length" class="json-block">{{ JSON.stringify(selected.metadata_json, null, 2) }}</pre>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import StatePanel from "@/components/ui/StatePanel.vue";
import { integrationApi, type IntegrationEvent } from "@/api/integrations";
const items = ref<IntegrationEvent[]>([]); const selected = ref<IntegrationEvent>(); const page = ref(1); const pageSize = ref(20); const total = ref(0); const loading = ref(false); const error = ref(false); const drawer = ref(false);
const filters = reactive({ event_type:"", source:"", status:"", subject:"" });
function params() { return { page:page.value, page_size:pageSize.value, ...(filters.event_type ? {event_type:filters.event_type}:{}), ...(filters.source ? {source:filters.source}:{}), ...(filters.status ? {status:filters.status}:{}), ...(filters.subject ? {subject:filters.subject}:{}) }; }
async function load() { loading.value=true; error.value=false; try { const response=await integrationApi.integrationEvents(params()); items.value=response.data.items; total.value=response.data.total; } catch { error.value=true; ElMessage.error("事件记录查询失败，请稍后重试"); } finally { loading.value=false; } }
function applyFilters() { page.value=1; void load(); }
function open(row:IntegrationEvent) { selected.value=row; drawer.value=true; }
function formatTime(value:string) { const date=new Date(value); if(Number.isNaN(date.getTime())) return value; return date.toLocaleString("zh-CN",{hour12:false}); }
function statusLabel(status:string) { return ({pending:"待处理",processing:"处理中",delivered:"已送达",failed:"处理失败",dead_letter:"进入死信"} as Record<string,string>)[status] || status; }
function statusType(status:string) { if(status==="delivered") return "success"; if(status==="failed"||status==="dead_letter") return "danger"; if(status==="processing") return "warning"; return "info"; }
async function copy(value:string) { try { await navigator.clipboard.writeText(value); ElMessage.success("编号已复制"); } catch { ElMessage.error("复制失败，请手动复制"); } }
onMounted(load);
</script>

<style scoped>
.event-console{padding-top:4px}.toolbar{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:16px}.toolbar div{display:grid;gap:4px}.toolbar strong{color:#344054;font-size:14px}.toolbar span{color:#98a2b3;font-size:12px}.filters{margin-bottom:16px}.filters :deep(.el-input){width:190px}.event-summary{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:18px}.event-summary>div{display:grid;gap:5px;padding:12px;border:1px solid #eaecf0;border-radius:8px}.event-summary span{color:#98a2b3;font-size:11px}.event-summary strong{color:#344054;font-size:13px;word-break:break-all}.json-block{max-height:300px;overflow:auto;margin:0;padding:14px;border:1px solid #eaecf0;border-radius:8px;background:#f8fafc;font-size:12px;line-height:1.55;white-space:pre-wrap;word-break:break-word}@media(max-width:900px){.event-summary{grid-template-columns:repeat(2,1fr)}}
</style>
