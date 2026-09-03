<template>
  <SurfaceCard>
    <template #header><div class="runtime-header"><span>运行记录</span><el-button size="small" @click="load">刷新</el-button></div></template>
    <el-alert v-if="routeSourceLabel" :title="`执行来源：${routeSourceLabel}`" type="info" :closable="false" class="source-context" />
    <el-form inline @submit.prevent="search">
      <el-input v-model="filters.status" placeholder="状态" clearable @keyup.enter="search" />
      <el-input v-model="filters.agentId" placeholder="智能体 ID" clearable @keyup.enter="search" />
      <el-input v-model="filters.traceId" placeholder="链路 ID" clearable @keyup.enter="search" />
      <el-input v-model="filters.requestId" placeholder="请求 ID" clearable @keyup.enter="search" />
      <el-input v-model="filters.workflowId" placeholder="工作流 ID" clearable @keyup.enter="search" />
      <el-date-picker v-model="filters.startedRange" type="datetimerange" range-separator="至" start-placeholder="开始时间" end-placeholder="结束时间" clearable />
      <el-button type="primary" @click="search">查询</el-button><el-button @click="resetFilters">重置</el-button>
    </el-form>
    <el-alert v-if="error" type="error" :closable="false" title="运行记录查询失败，请稍后重试" />
    <StatePanel v-if="loading" state="loading" title="正在加载运行记录" description="正在同步 Execution 运行事实。" />
    <StatePanel v-else-if="!items.length" state="empty" title="暂无运行记录" description="当前筛选条件没有可展示的 Execution。" />
    <el-table v-else :data="items" @row-click="open">
      <el-table-column prop="execution_id" label="运行记录 ID" min-width="260"><template #default="{ row }"><el-button link type="primary" @click.stop="copyRuntimeId(row.execution_id)">{{ shortRuntimeId(row.execution_id) }}</el-button></template></el-table-column>
      <el-table-column label="状态" width="120"><template #default="{ row }"><el-tag :type="getRuntimeStatusMeta(row.status).type">{{ getRuntimeStatusMeta(row.status).label }}</el-tag></template></el-table-column>
      <el-table-column prop="workflow_id" label="工作流" min-width="220" /><el-table-column prop="agent_id" label="智能体" min-width="220" />
      <el-table-column label="链路 ID" min-width="220"><template #default="{ row }"><el-button link type="primary" @click.stop="copyRuntimeId(row.trace_id)">{{ shortRuntimeId(row.trace_id) }}</el-button></template></el-table-column>
      <el-table-column prop="started_at" label="开始时间" min-width="190" />
    </el-table>
    <el-pagination v-if="total" v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" @change="load" />
  </SurfaceCard>

  <el-drawer v-model="drawer" title="运行记录详情" size="60%">
    <el-alert v-if="detailError" type="error" :closable="false" title="运行记录详情查询失败" />
    <template v-else>
      <el-descriptions v-if="selected" :column="2" border>
        <el-descriptions-item label="运行记录 ID"><el-button link type="primary" @click="copyRuntimeId(selected.execution_id)">{{ shortRuntimeId(selected.execution_id) }}</el-button></el-descriptions-item>
        <el-descriptions-item label="状态"><el-tag :type="getRuntimeStatusMeta(selected.status).type">{{ getRuntimeStatusMeta(selected.status).label }}</el-tag></el-descriptions-item>
        <el-descriptions-item label="链路 ID"><el-button link type="primary" @click="copyRuntimeId(selected.trace_id)">{{ shortRuntimeId(selected.trace_id) }}</el-button></el-descriptions-item>
        <el-descriptions-item label="请求 ID"><el-button link type="primary" @click="copyRuntimeId(selected.request_id)">{{ shortRuntimeId(selected.request_id) }}</el-button></el-descriptions-item>
        <el-descriptions-item label="工作流 ID">{{ selected.workflow_id || "-" }}</el-descriptions-item><el-descriptions-item label="工作流版本">{{ selected.workflow_version_id || "-" }}</el-descriptions-item>
        <el-descriptions-item label="会话 ID">{{ selected.session_id || "-" }}</el-descriptions-item><el-descriptions-item label="智能体">{{ selected.agent_id || "-" }}</el-descriptions-item>
        <el-descriptions-item label="模型">{{ selected.model_id || "-" }}</el-descriptions-item><el-descriptions-item label="耗时">{{ formatLatency(selected.duration_ms) }}</el-descriptions-item>
      </el-descriptions>

      <SurfaceCard v-if="correlationReady" bordered>
        <template #header><div class="section-header"><span>执行可观测关联</span><el-tag type="success">Trigger → Execution → Trace → Audit</el-tag></div></template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="Trigger ID"><el-button v-if="triggerId" link type="primary" @click="copyRuntimeId(triggerId)">{{ shortRuntimeId(triggerId) }}</el-button><span v-else>-</span></el-descriptions-item>
          <el-descriptions-item label="Trigger 类型">{{ triggerTypeLabel }}</el-descriptions-item>
          <el-descriptions-item label="Execution ID"><el-button link type="primary" @click="copyRuntimeId(selected?.execution_id)">{{ shortRuntimeId(selected?.execution_id) }}</el-button></el-descriptions-item>
          <el-descriptions-item label="Trace ID"><el-button link type="primary" @click="copyRuntimeId(selected?.trace_id)">{{ shortRuntimeId(selected?.trace_id) }}</el-button></el-descriptions-item>
          <el-descriptions-item label="Audit 记录">{{ auditLogs.length }} 条</el-descriptions-item>
          <el-descriptions-item label="关联来源">{{ correlationSource }}</el-descriptions-item>
        </el-descriptions>
        <el-alert v-if="!triggerId" type="info" :closable="false" class="relation-note" title="当前后端 Contract 未提供独立 Execution → Trigger 外键；Trigger ID 仅从入口上下文或 Trace data.trigger_id 读取，不进行推断。" />
      </SurfaceCard>

      <SurfaceCard v-if="trigger" bordered>
        <template #header><div class="section-header"><span>Trigger</span><el-tag :type="trigger.status === 'enabled' ? 'success' : 'info'">{{ trigger.status }}</el-tag></div></template>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="名称">{{ trigger.name }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ triggerTypeLabel }}</el-descriptions-item>
          <el-descriptions-item label="Trigger ID">{{ trigger.id }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ trigger.created_at }}</el-descriptions-item>
        </el-descriptions>
      </SurfaceCard>

      <SurfaceCard bordered>
        <template #header><div class="section-header"><span>Audit 审计</span><el-tag>{{ auditLogs.length }}</el-tag></div></template>
        <StatePanel v-if="!auditLogs.length" state="empty" title="暂无审计记录" description="当前 Execution 没有可展示的审计事实。" />
        <el-table v-else :data="auditLogs" size="small">
          <el-table-column prop="action" label="操作" min-width="180" />
          <el-table-column prop="status" label="状态" width="120" />
          <el-table-column prop="error_code" label="错误代码" width="160" />
          <el-table-column prop="actor_id" label="操作人" min-width="180" />
          <el-table-column prop="created_at" label="时间" min-width="180" />
        </el-table>
      </SurfaceCard>

      <SurfaceCard v-if="workflowDetail" bordered>
        <template #header><div class="section-header"><span>Execution 关系</span><el-tag v-if="workflowDetail.retry_of_execution_id || workflowDetail.resume_of_execution_id" type="warning">派生 Execution</el-tag></div></template>
        <el-descriptions :column="2" border>
          <el-descriptions-item v-if="workflowDetail.retry_of_execution_id" label="Retry 来源"><el-button link type="primary" @click="navigateToExecution(workflowDetail.retry_of_execution_id)">{{ shortRuntimeId(workflowDetail.retry_of_execution_id) }}</el-button></el-descriptions-item>
          <el-descriptions-item v-if="workflowDetail.resume_of_execution_id" label="Resume 来源"><el-button link type="primary" @click="navigateToExecution(workflowDetail.resume_of_execution_id)">{{ shortRuntimeId(workflowDetail.resume_of_execution_id) }}</el-button></el-descriptions-item>
          <el-descriptions-item v-if="workflowDetail.resume_checkpoint_sequence !== undefined" label="恢复检查点序号">{{ workflowDetail.resume_checkpoint_sequence }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ workflowDetail.created_at }}</el-descriptions-item>
        </el-descriptions>
        <div v-if="children.length" class="child-executions">
          <div class="subsection-title">派生 Execution</div>
          <el-table :data="children" size="small">
            <el-table-column prop="id" label="Execution ID" min-width="260"><template #default="{ row }"><el-button link type="primary" @click="navigateToExecution(row.id)">{{ shortRuntimeId(row.id) }}</el-button></template></el-table-column>
            <el-table-column label="关系" width="120"><template #default="{ row }">{{ row.retry_of_execution_id === workflowDetail?.id ? "Retry" : "Resume" }}</template></el-table-column>
            <el-table-column prop="status" label="状态" width="120" />
            <el-table-column prop="created_at" label="创建时间" min-width="180" />
          </el-table>
        </div>
        <StatePanel v-else state="empty" title="暂无派生 Execution" description="当前 Execution 没有后端返回的 Retry / Resume 派生关系。" />
      </SurfaceCard>

      <el-alert v-if="selected" type="info" :closable="false" class="control-hint" title="以下操作直接调用 Workflow Execution 生命周期接口；父子关系以后端返回的 retry/resume 字段为准。" />
      <div v-if="selected" class="execution-actions">
        <el-button v-if="selected.status === 'pending'" type="primary" :loading="actionLoading" @click="runSelected">运行</el-button>
        <el-button v-if="selected.status === 'pending' || selected.status === 'running'" type="warning" :loading="actionLoading" @click="cancelSelected">取消执行</el-button>
        <el-button v-if="selected.status === 'failed'" :loading="actionLoading" @click="retrySelected">重试</el-button>
        <el-button v-if="selected.status === 'failed'" :loading="actionLoading" @click="resumeSelected">从检查点恢复</el-button>
      </div>

      <el-divider>运行时间线</el-divider><StatePanel v-if="!events.length" state="empty" title="暂无时间线事件" description="该 Execution 当前没有可展示的运行时间线。" /><el-timeline v-else><el-timeline-item v-for="event in events" :key="event.id" :timestamp="event.started_at"><div><strong>{{ displayRuntimeType(event.span_type) }}</strong> / {{ getRuntimeStatusMeta(event.status).label }} / {{ event.duration_ms ?? 0 }} 毫秒</div><el-descriptions v-if="event.span_type === 'retrieval' && event.metadata" :column="2" border style="margin-top: 8px"><el-descriptions-item label="Top K">{{ event.metadata.top_k }}</el-descriptions-item><el-descriptions-item label="结果数">{{ event.metadata.result_count }}</el-descriptions-item><el-descriptions-item label="检索来源">{{ Array.isArray(event.metadata.retrieval_sources) ? event.metadata.retrieval_sources.join(", ") : "-" }}</el-descriptions-item><el-descriptions-item label="引用">{{ Array.isArray(event.metadata.citations) ? event.metadata.citations.join(", ") : "-" }}</el-descriptions-item></el-descriptions></el-timeline-item></el-timeline>
      <el-divider>工作流运行链路</el-divider><StatePanel v-if="!traceItems.length" state="empty" title="暂无工作流运行链路事件" description="该 Execution 当前没有可展示的 Trace 事件。" /><el-timeline v-else><el-timeline-item v-for="item in traceItems" :key="item.id" :timestamp="item.created_at"><div><strong>{{ displayRuntimeEvent(item.event_type) }}</strong><span> / {{ getRuntimeStatusMeta(item.status).label }}</span><span v-if="item.node_id"> / 节点={{ item.node_id }}</span></div><el-descriptions :column="2" border style="margin-top: 8px"><el-descriptions-item label="链路 ID">{{ shortRuntimeId(item.trace_id) }}</el-descriptions-item><el-descriptions-item label="节点">{{ item.node_id || "-" }}</el-descriptions-item><el-descriptions-item v-if="item.error_code" label="错误代码">{{ displayRuntimeErrorCode(item.error_code) }}</el-descriptions-item><el-descriptions-item v-if="item.error_message" label="错误信息">{{ displayRuntimeError(item.error_code, item.error_message) }}</el-descriptions-item></el-descriptions><pre v-if="item.data" class="trace-data">{{ JSON.stringify(item.data, null, 2) }}</pre></el-timeline-item></el-timeline>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import StatePanel from "@/components/ui/StatePanel.vue";
import SurfaceCard from "@/components/ui/SurfaceCard.vue";
import { runtimeApi, type Event, type Execution, type WorkflowTraceItem, type AuditLog } from "@/api/runtime";
import { workflowApi, type WorkflowExecution, type WorkflowTrigger } from "@/api/workflows";
import { formatLatency, getRuntimeStatusMeta, shortRuntimeId } from "@/utils/runtime";

type DateRange = [Date, Date] | null;
const route = useRoute(); const router = useRouter();
const items = ref<Execution[]>([]), events = ref<Event[]>([]), traceItems = ref<WorkflowTraceItem[]>([]), selected = ref<Execution>();
const workflowDetail = ref<WorkflowExecution | null>(null), children = ref<WorkflowExecution[]>([]);
const trigger = ref<WorkflowTrigger | null>(null), auditLogs = ref<AuditLog[]>([]), triggerId = ref<string>("");
const page = ref(1), pageSize = ref(20), total = ref(0), loading = ref(false), error = ref(false), drawer = ref(false), detailError = ref(false), actionLoading = ref(false);
const filters = ref<{ status: string; agentId: string; traceId: string; requestId: string; workflowId: string; startedRange: DateRange }>({ status: "", agentId: "", traceId: "", requestId: "", workflowId: "", startedRange: null });
const runtimeTypeLabels: Record<string, string> = { retrieval: "检索", llm: "模型调用", tool: "工具调用", workflow: "工作流", agent: "智能体", scheduler: "调度", system: "系统" };
const runtimeEventLabels: Record<string, string> = { execution_started: "执行开始", execution_completed: "执行完成", execution_failed: "执行失败", execution_cancelled: "执行取消", node_started: "节点开始", node_completed: "节点完成", node_failed: "节点失败", tool_started: "工具开始", tool_completed: "工具完成", tool_failed: "工具失败", retrieval_started: "检索开始", retrieval_completed: "检索完成", retrieval_failed: "检索失败" };
const runtimeErrorLabels: Record<string, string> = { VALIDATION_ERROR: "参数校验失败", AUTHORIZATION_ERROR: "权限校验失败", NOT_FOUND: "资源不存在", TIMEOUT: "执行超时", PROVIDER_ERROR: "模型服务调用失败", TOOL_ERROR: "工具执行失败", RETRIEVAL_ERROR: "知识检索失败", HTTP_ERROR: "外部请求失败" };
const routeSourceLabel = computed(() => { const source = typeof route.query.source === "string" ? route.query.source : ""; return source === "workflow-trigger" ? "Workflow Trigger → Execution" : source === "webhook" ? "Webhook → Workflow Execution" : source === "scheduler" ? "Scheduler → Workflow Execution" : source === "runtime-relation" ? "Execution 关系追踪" : source ? source : ""; });
const correlationReady = computed(() => !!selected.value);
const triggerTypeLabel = computed(() => trigger.value ? `${trigger.value.trigger_type}（${trigger.value.trigger_type === "scheduled" ? "Scheduler" : trigger.value.trigger_type === "webhook" ? "Webhook" : "Manual"}）` : "未解析");
const correlationSource = computed(() => triggerId.value ? (typeof route.query.trigger_id === "string" ? "Trigger 入口上下文" : "Trace data.trigger_id") : "Execution / Trace ID");
function displayRuntimeType(value: unknown) { if (typeof value !== "string" || !value) return "未知类型"; return `${runtimeTypeLabels[value] || "未知类型"}（${value}）`; }
function displayRuntimeEvent(value: unknown) { if (typeof value !== "string" || !value) return "未知事件"; return `${runtimeEventLabels[value] || "未知事件"}（${value}）`; }
function displayRuntimeErrorCode(value: unknown) { if (typeof value !== "string" || !value) return "未知错误"; return `${runtimeErrorLabels[value] || "运行失败"}（${value}）`; }
function displayRuntimeError(code: unknown, message: unknown) { if (typeof code === "string" && code) return runtimeErrorLabels[code] || "运行失败，请根据错误代码排查"; return typeof message === "string" && message ? "运行失败，请查看错误详情" : "-"; }
function buildQuery() { const range = filters.value.startedRange; return { page: page.value, page_size: pageSize.value, ...(filters.value.status ? { status: filters.value.status.trim() } : {}), ...(filters.value.agentId ? { agent_id: filters.value.agentId.trim() } : {}), ...(filters.value.traceId ? { trace_id: filters.value.traceId.trim() } : {}), ...(filters.value.requestId ? { request_id: filters.value.requestId.trim() } : {}), ...(filters.value.workflowId ? { workflow_id: filters.value.workflowId.trim() } : {}), ...(range?.[0] ? { started_from: range[0].toISOString() } : {}), ...(range?.[1] ? { started_to: range[1].toISOString() } : {}) }; }
async function load() { loading.value = true; error.value = false; try { const r = await runtimeApi.executions(buildQuery()); items.value = r.data.items; total.value = r.data.total; const executionId = typeof route.query.execution_id === "string" ? route.query.execution_id : ""; if (executionId) { const row = items.value.find((item) => item.execution_id === executionId); if (row) await open(row); else await openById(executionId); } } catch (err) { console.error("运行记录查询失败", err); error.value = true; ElMessage.error("运行记录查询失败，请稍后重试"); } finally { loading.value = false; } }
function search() { page.value = 1; void load(); }
function resetFilters() { filters.value = { status: "", agentId: "", traceId: "", requestId: "", workflowId: "", startedRange: null }; page.value = 1; void load(); }
async function loadWorkflowRelation(id: string, workflowId?: string) { workflowDetail.value = null; children.value = []; if (!workflowId) return; try { const detail = await workflowApi.execution(id); workflowDetail.value = detail.data; const all = await workflowApi.listExecutions(workflowId); children.value = all.data.filter((item) => item.id !== id && (item.retry_of_execution_id === id || item.resume_of_execution_id === id)); } catch (err) { console.warn("Execution 关系查询失败", err); } }
function resolveTriggerId() { const routeTrigger = typeof route.query.trigger_id === "string" ? route.query.trigger_id : ""; if (routeTrigger) return routeTrigger; for (const item of traceItems.value) { const value = item.data?.trigger_id; if (typeof value === "string" && value) return value; } return ""; }
async function loadCorrelation(executionId: string, workflowId?: string) { trigger.value = null; auditLogs.value = []; triggerId.value = resolveTriggerId(); const tasks: Promise<unknown>[] = [runtimeApi.auditLogs({ execution_id: executionId, page: 1, page_size: 50 })]; if (workflowId) tasks.push(workflowApi.triggers(workflowId)); try { const [auditResult, triggerResult] = await Promise.all(tasks); auditLogs.value = (auditResult as { data: { items: AuditLog[] } }).data.items || []; if (triggerResult) { const triggers = (triggerResult as { data: WorkflowTrigger[] }).data; trigger.value = triggers.find((item) => item.id === triggerId.value) || null; } } catch (err) { console.warn("运行关联信息查询失败", err); } }
async function openById(id: string) { selected.value = undefined; workflowDetail.value = null; children.value = []; events.value = []; traceItems.value = []; trigger.value = null; auditLogs.value = []; triggerId.value = ""; detailError.value = false; drawer.value = true; try { const detail = await runtimeApi.execution(id); selected.value = detail.data.execution; const [timeline, trace] = await Promise.all([runtimeApi.executionEvents(id), runtimeApi.executionTrace(id)]); events.value = timeline.data.items; traceItems.value = trace.data.items; await loadCorrelation(id, detail.data.execution.workflow_id); await loadWorkflowRelation(id, detail.data.execution.workflow_id); } catch (err) { console.error("运行记录详情查询失败", err); detailError.value = true; ElMessage.error("运行记录详情查询失败，请稍后重试"); } }
async function open(row: Execution) { await openById(row.execution_id); }
async function refreshSelected(id: string) { await openById(id); }
async function navigateToExecution(id: string) { const workflowId = workflowDetail.value?.workflow_id || selected.value?.workflow_id; await router.push({ path: "/runtime", query: { execution_id: id, ...(workflowId ? { workflow_id: workflowId } : {}), source: "runtime-relation" } }); }
async function runSelected() { if (!selected.value) return; await executeAction("run", () => workflowApi.runExecution(selected.value!.execution_id), "Execution 已进入运行流程"); }
async function cancelSelected() { if (!selected.value) return; try { await ElMessageBox.confirm("取消后该 Execution 将进入终态，确认继续？", "危险操作确认", { type: "warning", confirmButtonText: "确认取消", cancelButtonText: "返回" }); await executeAction("cancel", () => workflowApi.cancelExecution(selected.value!.execution_id), "Execution 已取消"); } catch (error) { if (error !== "cancel") ElMessage.error("Execution 取消失败"); } }
async function retrySelected() { if (!selected.value) return; try { await ElMessageBox.confirm("将基于原失败 Execution 创建新的 Retry Execution，确认继续？", "确认重试", { type: "warning" }); await executeAction("retry", () => workflowApi.retryExecution(selected.value!.execution_id), "已创建 Retry Execution"); } catch (error) { if (error !== "cancel") ElMessage.error("Execution 重试失败"); } }
async function resumeSelected() { if (!selected.value) return; try { await ElMessageBox.confirm("将根据后端 Durable Resume 条件创建新的 Execution，确认继续？", "确认恢复", { type: "warning" }); await executeAction("resume", () => workflowApi.resumeExecution(selected.value!.execution_id), "已创建 Resume Execution"); } catch (error) { if (error !== "cancel") ElMessage.error("Execution 恢复失败"); } }
async function executeAction(action: string, operation: () => Promise<{ data: { id: string } }>, success: string) { actionLoading.value = true; try { const result = await operation(); ElMessage.success(success); await refreshSelected(result.data.id); } catch (error) { console.error(`Execution ${action} failed`, error); ElMessage.error(`Execution ${action === "run" ? "运行" : action === "cancel" ? "取消" : action === "retry" ? "重试" : "恢复"}失败，请稍后重试`); } finally { actionLoading.value = false; } }
async function copyRuntimeId(value: string | null | undefined) { if (!value) return; try { await navigator.clipboard.writeText(value); ElMessage.success("执行上下文已复制"); } catch (err) { console.error("复制执行上下文失败", err); ElMessage.error("复制失败，请手动复制"); } }
watch(() => route.query.execution_id, (id) => { if (typeof id === "string" && id && id !== selected.value?.execution_id) void openById(id); });
onMounted(load);
</script>

<style scoped>
.runtime-header,.section-header { display:flex; align-items:center; justify-content:space-between; }.source-context { margin-bottom:12px; }.execution-actions { display:flex; gap:8px; margin:12px 0; flex-wrap:wrap; }.relation-card { margin-top:16px; }.child-executions { margin-top:16px; }.subsection-title { margin-bottom:8px; font-weight:600; }.control-hint { margin:12px 0; }.relation-note { margin-top:12px; }.trace-data { max-height:320px; overflow:auto; padding:12px; background:var(--el-fill-color-light); border-radius:4px; white-space:pre-wrap; word-break:break-word; }
</style>
