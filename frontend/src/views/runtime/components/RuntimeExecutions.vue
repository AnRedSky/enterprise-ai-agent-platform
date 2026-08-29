<template>
  <el-card>
    <template #header>运行记录</template>
    <el-form inline @submit.prevent>
      <el-input v-model="status" placeholder="状态" clearable @keyup.enter="load" />
      <el-button type="primary" @click="load">查询</el-button>
    </el-form>
    <el-alert v-if="error" type="error" :closable="false" title="运行记录查询失败，请稍后重试" />
    <el-empty v-else-if="!loading && items.length === 0" description="暂无运行记录" />
    <el-table v-else :data="items" v-loading="loading" @row-click="open">
      <el-table-column prop="execution_id" label="运行记录 ID" min-width="260"><template #default="{ row }"><el-button link type="primary" @click.stop="copyRuntimeId(row.execution_id)">{{ shortRuntimeId(row.execution_id) }}</el-button></template></el-table-column>
      <el-table-column label="状态" width="120"><template #default="{ row }"><el-tag :type="getRuntimeStatusMeta(row.status).type">{{ getRuntimeStatusMeta(row.status).label }}</el-tag></template></el-table-column>
      <el-table-column prop="agent_id" label="智能体" min-width="220" />
      <el-table-column label="链路 ID" min-width="220"><template #default="{ row }"><el-button link type="primary" @click.stop="copyRuntimeId(row.trace_id)">{{ shortRuntimeId(row.trace_id) }}</el-button></template></el-table-column>
      <el-table-column prop="started_at" label="开始时间" min-width="190" />
    </el-table>
    <el-pagination v-if="total" v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" @change="load" />
  </el-card>
  <el-drawer v-model="drawer" title="运行记录详情" size="60%">
    <el-alert v-if="detailError" type="error" :closable="false" title="运行记录详情查询失败" />
    <template v-else>
      <el-descriptions v-if="selected" :column="2" border>
        <el-descriptions-item label="运行记录 ID"><el-button link type="primary" @click="copyRuntimeId(selected.execution_id)">{{ shortRuntimeId(selected.execution_id) }}</el-button></el-descriptions-item>
        <el-descriptions-item label="状态"><el-tag :type="getRuntimeStatusMeta(selected.status).type">{{ getRuntimeStatusMeta(selected.status).label }}</el-tag></el-descriptions-item>
        <el-descriptions-item label="链路 ID"><el-button link type="primary" @click="copyRuntimeId(selected.trace_id)">{{ shortRuntimeId(selected.trace_id) }}</el-button></el-descriptions-item>
        <el-descriptions-item label="请求 ID"><el-button link type="primary" @click="copyRuntimeId(selected.request_id)">{{ shortRuntimeId(selected.request_id) }}</el-button></el-descriptions-item>
        <el-descriptions-item label="会话 ID"><el-button link type="primary" @click="copyRuntimeId(selected.session_id)">{{ shortRuntimeId(selected.session_id) }}</el-button></el-descriptions-item>
        <el-descriptions-item label="智能体">{{ selected.agent_id || "-" }}</el-descriptions-item>
        <el-descriptions-item label="模型">{{ selected.model_id || "-" }}</el-descriptions-item>
        <el-descriptions-item label="耗时">{{ formatLatency(selected.duration_ms) }}</el-descriptions-item>
      </el-descriptions>
      <el-divider>运行时间线</el-divider>
      <el-empty v-if="!events.length" description="暂无时间线事件" />
      <el-timeline v-else><el-timeline-item v-for="event in events" :key="event.id" :timestamp="event.started_at"><div><strong>{{ displayRuntimeType(event.span_type) }}</strong> / {{ getRuntimeStatusMeta(event.status).label }} / {{ event.duration_ms ?? 0 }} 毫秒</div><el-descriptions v-if="event.span_type === 'retrieval' && event.metadata" :column="2" border style="margin-top: 8px"><el-descriptions-item label="Top K">{{ event.metadata.top_k }}</el-descriptions-item><el-descriptions-item label="结果数">{{ event.metadata.result_count }}</el-descriptions-item><el-descriptions-item label="检索来源">{{ Array.isArray(event.metadata.retrieval_sources) ? event.metadata.retrieval_sources.join(", ") : "-" }}</el-descriptions-item><el-descriptions-item label="引用">{{ Array.isArray(event.metadata.citations) ? event.metadata.citations.join(", ") : "-" }}</el-descriptions-item></el-descriptions></el-timeline-item></el-timeline>
      <el-divider>工作流运行链路</el-divider>
      <el-empty v-if="!traceItems.length" description="暂无工作流运行链路事件" />
      <el-timeline v-else><el-timeline-item v-for="item in traceItems" :key="item.id" :timestamp="item.created_at"><div><strong>{{ displayRuntimeEvent(item.event_type) }}</strong><span> / {{ getRuntimeStatusMeta(item.status).label }}</span><span v-if="item.node_id"> / 节点={{ item.node_id }}</span></div><el-descriptions :column="2" border style="margin-top: 8px"><el-descriptions-item label="链路 ID">{{ shortRuntimeId(item.trace_id) }}</el-descriptions-item><el-descriptions-item label="节点">{{ item.node_id || "-" }}</el-descriptions-item><el-descriptions-item v-if="item.error_code" label="错误代码">{{ displayRuntimeErrorCode(item.error_code) }}</el-descriptions-item><el-descriptions-item v-if="item.error_message" label="错误信息">{{ displayRuntimeError(item.error_code, item.error_message) }}</el-descriptions-item></el-descriptions><pre v-if="item.data" class="trace-data">{{ JSON.stringify(item.data, null, 2) }}</pre></el-timeline-item></el-timeline>
    </template>
  </el-drawer>
</template>
<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { runtimeApi, type Event, type Execution, type WorkflowTraceItem } from "@/api/runtime";
import { formatLatency, getRuntimeStatusMeta, shortRuntimeId } from "@/utils/runtime";
const items = ref<Execution[]>([]), events = ref<Event[]>([]), traceItems = ref<WorkflowTraceItem[]>([]), selected = ref<Execution>();
const page = ref(1), pageSize = ref(20), total = ref(0), status = ref(""), loading = ref(false), error = ref(false), drawer = ref(false), detailError = ref(false);
const runtimeTypeLabels: Record<string, string> = { retrieval: "检索", llm: "模型调用", tool: "工具调用", workflow: "工作流", agent: "智能体", scheduler: "调度", system: "系统" };
const runtimeEventLabels: Record<string, string> = { execution_started: "执行开始", execution_completed: "执行完成", execution_failed: "执行失败", execution_cancelled: "执行取消", node_started: "节点开始", node_completed: "节点完成", node_failed: "节点失败", tool_started: "工具开始", tool_completed: "工具完成", tool_failed: "工具失败", retrieval_started: "检索开始", retrieval_completed: "检索完成", retrieval_failed: "检索失败" };
const runtimeErrorLabels: Record<string, string> = { VALIDATION_ERROR: "参数校验失败", AUTHORIZATION_ERROR: "权限校验失败", NOT_FOUND: "资源不存在", TIMEOUT: "执行超时", PROVIDER_ERROR: "模型服务调用失败", TOOL_ERROR: "工具执行失败", RETRIEVAL_ERROR: "知识检索失败", HTTP_ERROR: "外部请求失败" };
function displayRuntimeType(value: unknown) { if (typeof value !== "string" || !value) return "未知类型"; return `${runtimeTypeLabels[value] || "未知类型"}（${value}）`; }
function displayRuntimeEvent(value: unknown) { if (typeof value !== "string" || !value) return "未知事件"; return `${runtimeEventLabels[value] || "未知事件"}（${value}）`; }
function displayRuntimeErrorCode(value: unknown) { if (typeof value !== "string" || !value) return "未知错误"; return `${runtimeErrorLabels[value] || "运行失败"}（${value}）`; }
function displayRuntimeError(code: unknown, message: unknown) { if (typeof code === "string" && code) return runtimeErrorLabels[code] || "运行失败，请根据错误代码排查"; return typeof message === "string" && message ? "运行失败，请查看错误详情" : "-"; }
async function load() { loading.value = true; error.value = false; try { const r = await runtimeApi.executions({ page: page.value, page_size: pageSize.value, ...(status.value ? { status: status.value } : {}) }); items.value = r.data.items; total.value = r.data.total; } catch (err) { console.error("运行记录查询失败", err); error.value = true; ElMessage.error("运行记录查询失败，请稍后重试"); } finally { loading.value = false; } }
async function open(row: Execution) { selected.value = row; events.value = []; traceItems.value = []; detailError.value = false; drawer.value = true; try { const [timeline, trace] = await Promise.all([runtimeApi.executionEvents(row.execution_id), runtimeApi.executionTrace(row.execution_id)]); events.value = timeline.data.items; traceItems.value = trace.data.items; } catch (err) { console.error("运行记录详情查询失败", err); detailError.value = true; ElMessage.error("运行记录详情查询失败，请稍后重试"); } }
async function copyRuntimeId(value: string | null | undefined) { if (!value) return; try { await navigator.clipboard.writeText(value); ElMessage.success("执行上下文已复制"); } catch (err) { console.error("复制执行上下文失败", err); ElMessage.error("复制失败，请手动复制"); } }
onMounted(load);
</script>
<style scoped>.trace-data { max-height: 220px; overflow: auto; margin: 8px 0 0; padding: 8px; white-space: pre-wrap; word-break: break-word; }</style>
