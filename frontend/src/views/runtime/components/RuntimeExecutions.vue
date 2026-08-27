<template>
  <el-card>
    <template #header>Runtime Executions</template>
    <el-form inline @submit.prevent>
      <el-input v-model="status" placeholder="Status" clearable @keyup.enter="load" />
      <el-button type="primary" @click="load">查询</el-button>
    </el-form>
    <el-alert v-if="error" type="error" :closable="false" title="Runtime 查询失败，请稍后重试" />
    <el-empty v-else-if="!loading && items.length === 0" description="暂无 Runtime Execution" />
    <el-table v-else :data="items" v-loading="loading" @row-click="open">
      <el-table-column prop="execution_id" label="Execution" min-width="260">
        <template #default="{ row }">
          <el-button link type="primary" @click.stop="copyRuntimeId(row.execution_id)">{{ shortRuntimeId(row.execution_id) }}</el-button>
        </template>
      </el-table-column>
      <el-table-column label="Status" width="120">
        <template #default="{ row }">
          <el-tag :type="getRuntimeStatusMeta(row.status).type">{{ getRuntimeStatusMeta(row.status).label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="agent_id" label="Agent" min-width="220" />
      <el-table-column label="Trace" min-width="220">
        <template #default="{ row }">
          <el-button link type="primary" @click.stop="copyRuntimeId(row.trace_id)">{{ shortRuntimeId(row.trace_id) }}</el-button>
        </template>
      </el-table-column>
      <el-table-column prop="started_at" label="Started" min-width="190" />
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
  </el-card>

  <el-drawer v-model="drawer" title="Execution Observability" size="60%">
    <el-alert v-if="detailError" type="error" :closable="false" title="Execution 可观测性查询失败" />
    <template v-else>
      <el-descriptions v-if="selected" :column="2" border>
        <el-descriptions-item label="Execution">
          <el-button link type="primary" @click="copyRuntimeId(selected.execution_id)">{{ shortRuntimeId(selected.execution_id) }}</el-button>
        </el-descriptions-item>
        <el-descriptions-item label="Status">
          <el-tag :type="getRuntimeStatusMeta(selected.status).type">{{ getRuntimeStatusMeta(selected.status).label }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="Trace">
          <el-button link type="primary" @click="copyRuntimeId(selected.trace_id)">{{ shortRuntimeId(selected.trace_id) }}</el-button>
        </el-descriptions-item>
        <el-descriptions-item label="Request">
          <el-button link type="primary" @click="copyRuntimeId(selected.request_id)">{{ shortRuntimeId(selected.request_id) }}</el-button>
        </el-descriptions-item>
        <el-descriptions-item label="Session">
          <el-button link type="primary" @click="copyRuntimeId(selected.session_id)">{{ shortRuntimeId(selected.session_id) }}</el-button>
        </el-descriptions-item>
        <el-descriptions-item label="Agent">{{ selected.agent_id || "-" }}</el-descriptions-item>
        <el-descriptions-item label="Model">{{ selected.model_id || "-" }}</el-descriptions-item>
        <el-descriptions-item label="Latency">{{ formatLatency(selected.duration_ms) }}</el-descriptions-item>
      </el-descriptions>

      <el-divider>Runtime Timeline</el-divider>
      <el-empty v-if="!events.length" description="暂无 Timeline Event" />
      <el-timeline v-else>
        <el-timeline-item v-for="event in events" :key="event.id" :timestamp="event.started_at">
          <div><strong>{{ event.span_type }}</strong> / {{ event.status }} / {{ event.duration_ms ?? 0 }} ms</div>
          <el-descriptions v-if="event.span_type === 'retrieval' && event.metadata" :column="2" border style="margin-top: 8px">
            <el-descriptions-item label="Top K">{{ event.metadata.top_k }}</el-descriptions-item>
            <el-descriptions-item label="Results">{{ event.metadata.result_count }}</el-descriptions-item>
            <el-descriptions-item label="Sources">
              {{ Array.isArray(event.metadata.retrieval_sources) ? event.metadata.retrieval_sources.join(", ") : "-" }}
            </el-descriptions-item>
            <el-descriptions-item label="Citations">
              {{ Array.isArray(event.metadata.citations) ? event.metadata.citations.join(", ") : "-" }}
            </el-descriptions-item>
          </el-descriptions>
        </el-timeline-item>
      </el-timeline>

      <el-divider>Workflow Trace</el-divider>
      <el-empty v-if="!traceItems.length" description="暂无 Workflow Trace Event" />
      <el-timeline v-else>
        <el-timeline-item v-for="item in traceItems" :key="item.id" :timestamp="item.created_at">
          <div>
            <strong>{{ item.event_type }}</strong>
            <span> / {{ item.status }}</span>
            <span v-if="item.node_id"> / node={{ item.node_id }}</span>
          </div>
          <el-descriptions :column="2" border style="margin-top: 8px">
            <el-descriptions-item label="Trace ID">{{ shortRuntimeId(item.trace_id) }}</el-descriptions-item>
            <el-descriptions-item label="Node">{{ item.node_id || "-" }}</el-descriptions-item>
            <el-descriptions-item v-if="item.error_code" label="Error Code">{{ item.error_code }}</el-descriptions-item>
            <el-descriptions-item v-if="item.error_message" label="Error">{{ item.error_message }}</el-descriptions-item>
          </el-descriptions>
          <pre v-if="item.data" class="trace-data">{{ JSON.stringify(item.data, null, 2) }}</pre>
        </el-timeline-item>
      </el-timeline>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { runtimeApi, type Event, type Execution, type WorkflowTraceItem } from "@/api/runtime";
import { formatLatency, getRuntimeStatusMeta, shortRuntimeId } from "@/utils/runtime";

const items = ref<Execution[]>([]),
  events = ref<Event[]>([]),
  traceItems = ref<WorkflowTraceItem[]>([]),
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
  traceItems.value = [];
  detailError.value = false;
  drawer.value = true;
  try {
    const [timeline, trace] = await Promise.all([
      runtimeApi.executionEvents(row.execution_id),
      runtimeApi.executionTrace(row.execution_id),
    ]);
    events.value = timeline.data.items;
    traceItems.value = trace.data.items;
  } catch {
    detailError.value = true;
    ElMessage.error("Execution 可观测性查询失败");
  }
}

async function copyRuntimeId(value: string | null | undefined) {
  if (!value) return;
  try {
    await navigator.clipboard.writeText(value);
    ElMessage.success("执行上下文已复制");
  } catch {
    ElMessage.error("复制失败，请手动复制");
  }
}

onMounted(load);
</script>

<style scoped>
.trace-data {
  max-height: 220px;
  overflow: auto;
  margin: 8px 0 0;
  padding: 8px;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
