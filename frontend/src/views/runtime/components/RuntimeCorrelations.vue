<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { runtimeCorrelationsApi, type RuntimeCorrelationAudit, type RuntimeCorrelationResponse, type RuntimeCorrelationTrace } from "@/api/runtimeCorrelations";
import { shortRuntimeId } from "@/utils/runtime";

type FocusType = "execution" | "trace" | "audit" | "operator-action";
const route = useRoute();
const router = useRouter();
const routeFocusType = typeof route.query.focus_type === "string" ? route.query.focus_type : "";
const routeFocusId = typeof route.query.focus_id === "string" ? route.query.focus_id : "";
const focusType = ref<FocusType>(["execution", "trace", "audit", "operator-action"].includes(routeFocusType) ? routeFocusType as FocusType : "execution");
const focusId = ref(routeFocusId || (typeof route.query.execution_id === "string" ? route.query.execution_id : ""));
const loading = ref(false);
const error = ref("");
const result = ref<RuntimeCorrelationResponse | null>(null);
const tracePage = ref(1);
const auditPage = ref(1);
const selectedTraceId = ref("");
const selectedAuditId = ref("");
const focusLabel = computed(() => ({ execution: "Execution", trace: "Trace", audit: "Audit", "operator-action": "Operator Action" }[focusType.value]));
const focusedTrace = computed<RuntimeCorrelationTrace | null>(() => {
  const id = selectedTraceId.value || (focusType.value === "trace" ? focusId.value : "");
  return result.value?.focused_traces?.find((item) => item.trace_id === id) ?? result.value?.traces.items.find((item) => item.trace_id === id) ?? null;
});
const focusedAudit = computed<RuntimeCorrelationAudit | null>(() => {
  const id = selectedAuditId.value || (focusType.value === "audit" ? focusId.value : result.value?.focus_audit_id || "");
  return result.value?.focused_audit?.id === id ? result.value.focused_audit : result.value?.audits.items.find((item) => item.id === id) ?? null;
});
function focusRoute() {
  return focusType.value === "execution" ? runtimeCorrelationsApi.execution : focusType.value === "trace" ? runtimeCorrelationsApi.trace : focusType.value === "audit" ? runtimeCorrelationsApi.audit : runtimeCorrelationsApi.operatorAction;
}
async function query() {
  if (!focusId.value.trim()) { error.value = "请输入关联对象 ID"; return; }
  loading.value = true; error.value = "";
  selectedTraceId.value = "";
  selectedAuditId.value = "";
  try {
    result.value = (await focusRoute()(focusId.value.trim(), { trace_page: tracePage.value, trace_page_size: 20, audit_page: auditPage.value, audit_page_size: 20 })).data;
  } catch { result.value = null; error.value = "关联查询失败，可能对象不存在或不属于当前租户"; }
  finally { loading.value = false; }
}
function setTracePage(page: number) { tracePage.value = page; void query(); }
function setAuditPage(page: number) { auditPage.value = page; void query(); }
async function copy(value: string | null | undefined) { if (!value) return; await navigator.clipboard.writeText(value); ElMessage.success("已复制 ID"); }
function openExecution() {
  if (!result.value?.execution) return;
  const execution = result.value.execution;
  void router.push({ path: "/runtime", query: { tab: "executions", source: "runtime-correlation", execution_id: execution.id, workflow_id: execution.workflow_id, workflow_version_id: execution.workflow_version_id } });
}
function openWorkflowLifecycle(fact?: RuntimeCorrelationTrace | RuntimeCorrelationAudit) {
  if (!result.value?.execution) return;
  const execution = result.value.execution;
  const resolvedFact = fact ?? focusedTrace.value ?? focusedAudit.value ?? null;
  const isTrace = Boolean(resolvedFact && "execution_id" in resolvedFact);
  const isAudit = Boolean(resolvedFact && "workflow_execution_id" in resolvedFact);
  const executionId = isTrace ? (resolvedFact as RuntimeCorrelationTrace).execution_id : isAudit ? (resolvedFact as RuntimeCorrelationAudit).workflow_execution_id || execution.id : execution.id;
  const workflowId = resolvedFact?.workflow_id || execution.workflow_id;
  const query: Record<string, string> = { workflow_id: workflowId, execution_id: executionId, source: "runtime-correlation" };
  if (isTrace && (resolvedFact as RuntimeCorrelationTrace).trace_id) query.trace_id = (resolvedFact as RuntimeCorrelationTrace).trace_id;
  else if (isAudit && resolvedFact?.id) query.audit_id = resolvedFact.id;
  else if (focusType.value === "trace" && focusId.value) query.trace_id = focusId.value;
  else if (focusType.value === "audit" && focusId.value) query.audit_id = focusId.value;
  void router.push({ path: "/workflows/lifecycle", query });
}
function openTrace(traceId: string) {
  if (!traceId) return;
  selectedTraceId.value = traceId;
  const trace = result.value?.focused_traces?.find((item) => item.trace_id === traceId) ?? result.value?.traces.items.find((item) => item.trace_id === traceId);
  const execution = result.value?.execution;
  void router.push({ path: "/runtime", query: { tab: "correlations", source: "runtime-correlation", focus_type: "trace", focus_id: traceId, execution_id: trace?.execution_id || execution?.id || "", workflow_id: trace?.workflow_id || execution?.workflow_id || "", workflow_version_id: trace?.workflow_version_id || execution?.workflow_version_id || "" } });
}
function openAudit(auditId: string) {
  if (!auditId) return;
  selectedAuditId.value = auditId;
  const audit = result.value?.focused_audit?.id === auditId ? result.value.focused_audit : result.value?.audits.items.find((item) => item.id === auditId);
  const execution = result.value?.execution;
  void router.push({ path: "/runtime", query: { tab: "correlations", source: "runtime-correlation", focus_type: "audit", focus_id: auditId, execution_id: audit?.workflow_execution_id || execution?.id || "", workflow_id: audit?.workflow_id || execution?.workflow_id || "", workflow_version_id: audit?.workflow_version_id || execution?.workflow_version_id || "" } });
}
function openAuditTrace(traceId: string) { if (traceId) openTrace(traceId); }
function selectTrace(trace: RuntimeCorrelationTrace) { selectedTraceId.value = trace.trace_id; }
function selectAudit(audit: RuntimeCorrelationAudit) { selectedAuditId.value = audit.id; }
</script>

<template>
  <section class="correlation-workspace" aria-label="Audit Trace 关联工作台">
    <header class="section-heading"><div><span class="eyebrow">P2.10-II / II-04</span><h2>Audit / Trace 关联</h2><p>围绕一个 Durable Fact 双向展开 Execution、Trace、Audit 与 Operator Action。</p></div><el-tag type="info" effect="plain">只读 / Tenant Scoped</el-tag></header>
    <el-form inline @submit.prevent="query"><el-select v-model="focusType" style="width: 180px"><el-option label="Execution" value="execution" /><el-option label="Trace" value="trace" /><el-option label="Audit" value="audit" /><el-option label="Operator Action" value="operator-action" /></el-select><el-input v-model="focusId" clearable :placeholder="`输入 ${focusLabel} ID`" style="width: 360px" @keyup.enter="query" /><el-button type="primary" :loading="loading" @click="query">查询关联</el-button></el-form>
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <el-empty v-else-if="!result && !loading" description="输入对象 ID 开始关联查询" />
    <template v-if="result">
      <el-card shadow="never" class="relation-card"><template #header><div class="card-title"><span>Execution</span><div class="card-actions"><el-button v-if="result.execution" size="small" plain @click="openExecution">进入 Execution</el-button><el-button v-if="result.execution" size="small" type="primary" plain @click="openWorkflowLifecycle()">定位 Workflow</el-button><el-tag v-if="result.execution" :type="result.execution.status === 'failed' ? 'danger' : 'success'">{{ result.execution.status }}</el-tag></div></div></template><el-empty v-if="!result.execution" description="没有可访问的 Execution" :image-size="60" /><el-descriptions v-else :column="2" border><el-descriptions-item label="Execution ID"><el-button link type="primary" @click="copy(result.execution.id)">{{ shortRuntimeId(result.execution.id) }}</el-button></el-descriptions-item><el-descriptions-item label="Workflow ID">{{ shortRuntimeId(result.execution.workflow_id) }}</el-descriptions-item><el-descriptions-item label="Workflow Version">{{ shortRuntimeId(result.execution.workflow_version_id) }}</el-descriptions-item><el-descriptions-item label="状态">{{ result.execution.status }}</el-descriptions-item><el-descriptions-item label="错误代码">{{ result.execution.error_code || "-" }}</el-descriptions-item><el-descriptions-item label="创建时间">{{ result.execution.created_at }}</el-descriptions-item></el-descriptions></el-card>
      <el-card shadow="never" class="relation-card"><template #header><div class="card-title"><span>Trace</span><el-tag>{{ result.traces.total }}</el-tag></div></template><el-table :data="result.traces.items" size="small" highlight-current-row @row-click="selectTrace"><el-table-column prop="event_type" label="事件" min-width="180" /><el-table-column prop="node_id" label="节点" min-width="140" /><el-table-column prop="status" label="状态" width="110" /><el-table-column label="Trace ID" min-width="200"><template #default="{ row }"><el-button link type="primary" @click.stop="openTrace(row.trace_id)">{{ shortRuntimeId(row.trace_id) }}</el-button></template></el-table-column><el-table-column prop="error_code" label="错误代码" min-width="150" /><el-table-column prop="created_at" label="时间" min-width="180" /></el-table><el-pagination v-if="result.traces.total > result.traces.page_size" :current-page="result.traces.page" :page-size="result.traces.page_size" :total="result.traces.total" layout="prev, pager, next" @current-change="setTracePage" /></el-card>
      <el-card v-if="focusedTrace" shadow="never" class="fact-card"><template #header><div class="card-title"><span>Trace 具体事实</span><div class="card-actions"><el-button link type="primary" @click="copy(focusedTrace.trace_id)">复制 Trace ID</el-button><el-button size="small" type="primary" plain @click="openWorkflowLifecycle(focusedTrace)">定位 Workflow</el-button></div></div></template><el-descriptions :column="2" border><el-descriptions-item label="Trace ID">{{ focusedTrace.trace_id }}</el-descriptions-item><el-descriptions-item label="事件">{{ focusedTrace.event_type }}</el-descriptions-item><el-descriptions-item label="Execution ID">{{ focusedTrace.execution_id }}</el-descriptions-item><el-descriptions-item label="Workflow ID">{{ focusedTrace.workflow_id }}</el-descriptions-item><el-descriptions-item label="Workflow Version">{{ focusedTrace.workflow_version_id }}</el-descriptions-item><el-descriptions-item label="Node ID">{{ focusedTrace.node_id || "-" }}</el-descriptions-item><el-descriptions-item label="Actor ID">{{ focusedTrace.actor_id || "-" }}</el-descriptions-item><el-descriptions-item label="状态">{{ focusedTrace.status }}</el-descriptions-item><el-descriptions-item label="错误代码">{{ focusedTrace.error_code || "-" }}</el-descriptions-item><el-descriptions-item label="错误信息" :span="2">{{ focusedTrace.error_message || "-" }}</el-descriptions-item><el-descriptions-item label="Data" :span="2"><pre class="fact-json">{{ focusedTrace.data ? JSON.stringify(focusedTrace.data, null, 2) : "-" }}</pre></el-descriptions-item></el-descriptions></el-card>
      <el-card shadow="never" class="relation-card"><template #header><div class="card-title"><span>Audit</span><el-tag>{{ result.audits.total }}</el-tag></div></template><el-table :data="result.audits.items" size="small" highlight-current-row @row-click="selectAudit"><el-table-column prop="action" label="操作" min-width="220" /><el-table-column prop="status" label="状态" width="110" /><el-table-column prop="actor_id" label="操作人" min-width="180" /><el-table-column label="Audit ID" min-width="200"><template #default="{ row }"><el-button link type="primary" @click.stop="openAudit(row.id)">{{ shortRuntimeId(row.id) }}</el-button></template></el-table-column><el-table-column label="Trace ID" min-width="200"><template #default="{ row }"><el-button v-if="row.trace_id" link type="primary" @click.stop="openAuditTrace(row.trace_id)">{{ shortRuntimeId(row.trace_id) }}</el-button><span v-else>-</span></template></el-table-column><el-table-column prop="error_code" label="错误代码" min-width="150" /><el-table-column prop="created_at" label="时间" min-width="180" /></el-table><el-pagination v-if="result.audits.total > result.audits.page_size" :current-page="result.audits.page" :page-size="result.audits.page_size" :total="result.audits.total" layout="prev, pager, next" @current-change="setAuditPage" /></el-card>
      <el-card v-if="focusedAudit" shadow="never" class="fact-card"><template #header><div class="card-title"><span>Audit 具体事实</span><div class="card-actions"><el-button link type="primary" @click="copy(focusedAudit.id)">复制 Audit ID</el-button><el-button v-if="focusedAudit.trace_id" size="small" plain @click="openAuditTrace(focusedAudit.trace_id)">定位 Trace</el-button><el-button size="small" type="primary" plain @click="openWorkflowLifecycle(focusedAudit)">定位 Workflow</el-button></div></div></template><el-descriptions :column="2" border><el-descriptions-item label="Audit ID">{{ focusedAudit.id }}</el-descriptions-item><el-descriptions-item label="操作">{{ focusedAudit.action }}</el-descriptions-item><el-descriptions-item label="Execution ID">{{ focusedAudit.workflow_execution_id || "-" }}</el-descriptions-item><el-descriptions-item label="Workflow ID">{{ focusedAudit.workflow_id || "-" }}</el-descriptions-item><el-descriptions-item label="Workflow Version">{{ focusedAudit.workflow_version_id || "-" }}</el-descriptions-item><el-descriptions-item label="Trace ID">{{ focusedAudit.trace_id || "-" }}</el-descriptions-item><el-descriptions-item label="Actor ID">{{ focusedAudit.actor_id || "-" }}</el-descriptions-item><el-descriptions-item label="Resource">{{ focusedAudit.resource_type }} / {{ focusedAudit.resource_id || "-" }}</el-descriptions-item><el-descriptions-item label="Request ID">{{ focusedAudit.request_id || "-" }}</el-descriptions-item><el-descriptions-item label="状态">{{ focusedAudit.status }}</el-descriptions-item><el-descriptions-item label="错误代码">{{ focusedAudit.error_code || "-" }}</el-descriptions-item><el-descriptions-item label="Metadata" :span="2"><pre class="fact-json">{{ focusedAudit.metadata ? JSON.stringify(focusedAudit.metadata, null, 2) : "-" }}</pre></el-descriptions-item></el-descriptions></el-card>
      <el-card shadow="never" class="relation-card"><template #header><div class="card-title"><span>Operator Action</span><el-tag>{{ result.operator_actions.length }}</el-tag></div></template><el-empty v-if="!result.operator_actions.length" description="暂无关联 Operator Action" :image-size="50" /><el-table v-else :data="result.operator_actions" size="small"><el-table-column prop="action" label="动作" width="180" /><el-table-column prop="status" label="状态" width="110" /><el-table-column prop="actor_id" label="操作人" min-width="200" /><el-table-column prop="idempotency_key" label="幂等键" min-width="220" /><el-table-column prop="created_at" label="时间" min-width="180" /></el-table></el-card>
    </template>
  </section>
</template>

<style scoped>
.correlation-workspace{padding:4px 0}.section-heading{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:18px}.eyebrow{font-size:12px;letter-spacing:.08em;color:var(--el-text-color-secondary)}.section-heading h2{margin:4px 0 6px}.section-heading p{margin:0;color:var(--el-text-color-secondary)}.relation-card,.fact-card{margin-top:16px}.card-title{display:flex;align-items:center;justify-content:space-between;gap:12px}.card-actions{display:flex;align-items:center;gap:8px}.fact-json{margin:0;white-space:pre-wrap;word-break:break-word;max-height:320px;overflow:auto}.el-pagination{margin-top:12px;justify-content:flex-end}@media (max-width: 900px){.section-heading{flex-direction:column}.section-heading .el-tag{align-self:flex-start}.el-form{display:flex;flex-wrap:wrap}.el-form .el-input{width:min(100%,360px)!important}.card-actions{flex-wrap:wrap}.relation-card :deep(.el-descriptions){overflow-x:auto}}
</style>
