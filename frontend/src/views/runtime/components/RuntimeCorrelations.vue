<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { runtimeCorrelationsApi, type RuntimeCorrelationResponse } from "@/api/runtimeCorrelations";
import { shortRuntimeId } from "@/utils/runtime";

/** Runtime 深链关联工作区：只展示后端返回的 Durable Facts，不在前端复制关联规则。 */
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
const focusLabel = computed(() => ({ execution: "Execution", trace: "Trace", audit: "Audit", "operator-action": "Operator Action" }[focusType.value]));
function focusRoute() {
  return focusType.value === "execution" ? runtimeCorrelationsApi.execution : focusType.value === "trace" ? runtimeCorrelationsApi.trace : focusType.value === "audit" ? runtimeCorrelationsApi.audit : runtimeCorrelationsApi.operatorAction;
}
async function query() {
  if (!focusId.value.trim()) { error.value = "请输入关联对象 ID"; return; }
  loading.value = true; error.value = "";
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
function openWorkflowLifecycle() {
  if (!result.value?.execution) return;
  const execution = result.value.execution;
  const query: Record<string, string> = { workflow_id: execution.workflow_id, execution_id: execution.id, source: "runtime-correlation" };
  if (focusType.value === "trace" && focusId.value) query.trace_id = focusId.value;
  if (focusType.value === "audit" && focusId.value) query.audit_id = focusId.value;
  void router.push({ path: "/workflows/lifecycle", query });
}
function openTrace(traceId: string) {
  if (!traceId) return;
  void router.push({ path: "/runtime", query: { tab: "correlations", source: "runtime-correlation", focus_type: "trace", focus_id: traceId, execution_id: result.value?.execution?.id || "", workflow_id: result.value?.execution?.workflow_id || "", workflow_version_id: result.value?.execution?.workflow_version_id || "" } });
}
function openAudit(auditId: string) {
  if (!auditId) return;
  void router.push({ path: "/runtime", query: { tab: "correlations", source: "runtime-correlation", focus_type: "audit", focus_id: auditId, execution_id: result.value?.execution?.id || "", workflow_id: result.value?.execution?.workflow_id || "", workflow_version_id: result.value?.execution?.workflow_version_id || "" } });
}
</script>

<template>
  <section class="correlation-workspace" aria-label="Audit Trace 关联工作台">
    <header class="section-heading"><div><span class="eyebrow">P2.10-II / II-04</span><h2>Audit / Trace 关联</h2><p>围绕一个 Durable Fact 双向展开 Execution、Trace、Audit 与 Operator Action。</p></div><el-tag type="info" effect="plain">只读 / Tenant Scoped</el-tag></header>
    <el-form inline @submit.prevent="query"><el-select v-model="focusType" style="width: 180px"><el-option label="Execution" value="execution" /><el-option label="Trace" value="trace" /><el-option label="Audit" value="audit" /><el-option label="Operator Action" value="operator-action" /></el-select><el-input v-model="focusId" clearable :placeholder="`输入 ${focusLabel} ID`" style="width: 360px" @keyup.enter="query" /><el-button type="primary" :loading="loading" @click="query">查询关联</el-button></el-form>
    <el-alert v-if="error" :title="error" type="error" :closable="false" />
    <el-empty v-else-if="!result && !loading" description="输入对象 ID 开始关联查询" />
    <template v-if="result">
      <el-card shadow="never" class="relation-card"><template #header><div class="card-title"><span>Execution</span><div class="card-actions"><el-button v-if="result.execution" size="small" plain @click="openExecution">进入 Execution</el-button><el-button v-if="result.execution" size="small" type="primary" plain @click="openWorkflowLifecycle">定位 Workflow</el-button><el-tag v-if="result.execution" :type="result.execution.status === 'failed' ? 'danger' : 'success'">{{ result.execution.status }}</el-tag></div></div></template><el-empty v-if="!result.execution" description="没有可访问的 Execution" :image-size="60" /><el-descriptions v-else :column="2" border><el-descriptions-item label="Execution ID"><el-button link type="primary" @click="copy(result.execution.id)">{{ shortRuntimeId(result.execution.id) }}</el-button></el-descriptions-item><el-descriptions-item label="Workflow ID">{{ shortRuntimeId(result.execution.workflow_id) }}</el-descriptions-item><el-descriptions-item label="Workflow Version">{{ shortRuntimeId(result.execution.workflow_version_id) }}</el-descriptions-item><el-descriptions-item label="状态">{{ result.execution.status }}</el-descriptions-item><el-descriptions-item label="错误代码">{{ result.execution.error_code || "-" }}</el-descriptions-item><el-descriptions-item label="创建时间">{{ result.execution.created_at }}</el-descriptions-item></el-descriptions></el-card>
      <el-card shadow="never" class="relation-card"><template #header><div class="card-title"><span>Trace</span><el-tag>{{ result.traces.total }}</el-tag></div></template><el-table :data="result.traces.items" size="small"><el-table-column prop="event_type" label="事件" min-width="220" /><el-table-column prop="status" label="状态" width="110" /><el-table-column label="Trace ID" min-width="200"><template #default="{ row }"><el-button link type="primary" @click="openTrace(row.trace_id)">{{ shortRuntimeId(row.trace_id) }}</el-button></template></el-table-column><el-table-column prop="created_at" label="时间" min-width="180" /></el-table><el-pagination v-if="result.traces.total > result.traces.page_size" :current-page="result.traces.page" :page-size="result.traces.page_size" :total="result.traces.total" layout="prev, pager, next" @current-change="setTracePage" /></el-card>
      <el-card shadow="never" class="relation-card"><template #header><div class="card-title"><span>Audit</span><el-tag>{{ result.audits.total }}</el-tag></div></template><el-table :data="result.audits.items" size="small"><el-table-column prop="action" label="操作" min-width="240" /><el-table-column prop="status" label="状态" width="110" /><el-table-column prop="actor_id" label="操作人" min-width="200" /><el-table-column label="Audit ID" min-width="200"><template #default="{ row }"><el-button link type="primary" @click="openAudit(row.id)">{{ shortRuntimeId(row.id) }}</el-button></template></el-table-column><el-table-column prop="trace_id" label="Trace ID" min-width="200" /><el-table-column prop="created_at" label="时间" min-width="180" /></el-table><el-pagination v-if="result.audits.total > result.audits.page_size" :current-page="result.audits.page" :page-size="result.audits.page_size" :total="result.audits.total" layout="prev, pager, next" @current-change="setAuditPage" /></el-card>
      <el-card shadow="never" class="relation-card"><template #header><div class="card-title"><span>Operator Action</span><el-tag>{{ result.operator_actions.length }}</el-tag></div></template><el-empty v-if="!result.operator_actions.length" description="暂无关联 Operator Action" :image-size="50" /><el-table v-else :data="result.operator_actions" size="small"><el-table-column prop="action" label="动作" width="180" /><el-table-column prop="status" label="状态" width="110" /><el-table-column prop="actor_id" label="操作人" min-width="200" /><el-table-column prop="idempotency_key" label="幂等键" min-width="220" /><el-table-column prop="created_at" label="时间" min-width="180" /></el-table></el-card>
    </template>
  </section>
</template>

<style scoped>
.correlation-workspace{padding:4px 0}.section-heading{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-bottom:18px}.eyebrow{font-size:10px;font-weight:700;letter-spacing:.08em;color:#667085}.section-heading h2{margin:4px 0;font-size:18px;color:#101828}.section-heading p{margin:0;font-size:12px;color:#667085}.relation-card{margin-top:14px}.card-title{display:flex;align-items:center;justify-content:space-between;gap:8px}.card-actions{display:flex;align-items:center;gap:8px}.el-pagination{margin-top:12px;justify-content:flex-end}@media(max-width:700px){.section-heading{flex-direction:column}.el-form{display:flex;flex-direction:column;align-items:stretch}.el-form .el-select,.el-form .el-input{width:100%!important}.card-actions{flex-wrap:wrap}}
</style>
