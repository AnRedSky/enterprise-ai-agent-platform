<template>
  <el-card
    ><template #header>Runtime Executions</template
    ><el-form inline @submit.prevent
      ><el-input
        v-model="status"
        placeholder="Status"
        clearable
        @keyup.enter="load"
      /><el-button type="primary" @click="load">查询</el-button></el-form
    ><el-alert
      v-if="error"
      type="error"
      :closable="false"
      title="Runtime 查询失败，请稍后重试" /><el-empty
      v-else-if="!loading && items.length === 0"
      description="暂无 Runtime Execution" /><el-table
      v-else
      :data="items"
      v-loading="loading"
      @row-click="open"
      ><el-table-column
        prop="execution_id"
        label="Execution"
        min-width="260" /><el-table-column
        prop="status"
        label="Status"
        width="120" /><el-table-column
        prop="agent_id"
        label="Agent"
        min-width="220" /><el-table-column
        prop="trace_id"
        label="Trace"
        min-width="220" /><el-table-column
        prop="started_at"
        label="Started"
        min-width="190" /></el-table
    ><el-pagination
      v-if="total"
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      :page-sizes="[10, 20, 50, 100]"
      layout="total, sizes, prev, pager, next"
      @change="load" /></el-card
  ><el-drawer v-model="drawer" title="Execution Timeline" size="55%"
    ><el-alert
      v-if="detailError"
      type="error"
      :closable="false"
      title="Timeline 查询失败"
    /><template v-else
      ><el-descriptions v-if="selected" :column="2" border
        ><el-descriptions-item label="Execution">{{
          selected.execution_id
        }}</el-descriptions-item
        ><el-descriptions-item label="Status">{{
          selected.status
        }}</el-descriptions-item
        ><el-descriptions-item label="Trace">{{
          selected.trace_id
        }}</el-descriptions-item
        ><el-descriptions-item label="Request">{{
          selected.request_id
        }}</el-descriptions-item></el-descriptions
      ><el-empty
        v-if="!events.length"
        description="暂无 Timeline Event"
      /><el-timeline v-else
        ><el-timeline-item
          v-for="event in events"
          :key="event.id"
          :timestamp="event.started_at"
          ><div>
            <strong>{{ event.span_type }}</strong> / {{ event.status }} /
            {{ event.duration_ms ?? 0 }} ms
          </div>
          <el-descriptions
            v-if="event.span_type === 'retrieval' && event.metadata"
            :column="2"
            border
            style="margin-top: 8px"
            ><el-descriptions-item label="Top K">{{
              event.metadata.top_k
            }}</el-descriptions-item
            ><el-descriptions-item label="Results">{{
              event.metadata.result_count
            }}</el-descriptions-item
            ><el-descriptions-item label="Sources">{{
              Array.isArray(event.metadata.retrieval_sources)
                ? event.metadata.retrieval_sources.join(", ")
                : "-"
            }}</el-descriptions-item
            ><el-descriptions-item label="Citations">{{
              Array.isArray(event.metadata.citations)
                ? event.metadata.citations.join(", ")
                : "-"
            }}</el-descriptions-item></el-descriptions
          ></el-timeline-item
        ></el-timeline
      ></template
    ></el-drawer
  >
</template>
<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { runtimeApi, type Event, type Execution } from "@/api/runtime";
const items = ref<Execution[]>([]),
  events = ref<Event[]>([]),
  selected = ref<Execution>();
const page = ref(1),
  pageSize = ref(20),
  total = ref(0),
  status = ref(""),
  loading = ref(false),
  error = ref(false),
  drawer = ref(false),
  detailError = ref(false);
async function load() {
  loading.value = true;
  error.value = false;
  try {
    const r = await runtimeApi.executions({
      page: page.value,
      page_size: pageSize.value,
      ...(status.value ? { status: status.value } : {}),
    });
    items.value = r.data.items;
    total.value = r.data.total;
  } catch {
    error.value = true;
    ElMessage.error("Runtime 查询失败");
  } finally {
    loading.value = false;
  }
}
async function open(row: Execution) {
  selected.value = row;
  events.value = [];
  detailError.value = false;
  drawer.value = true;
  try {
    events.value = (
      await runtimeApi.executionEvents(row.execution_id)
    ).data.items;
  } catch {
    detailError.value = true;
    ElMessage.error("Execution Timeline 查询失败");
  }
}
onMounted(load);
</script>
