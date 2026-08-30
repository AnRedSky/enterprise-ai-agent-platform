<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import RuntimeExecutions from "./RuntimeExecutions.vue";
import RuntimeObservabilityOverview from "./RuntimeObservabilityOverview.vue";

const route = useRoute();
const router = useRouter();

const runtimeContextKeys = [
  "execution_id",
  "status",
  "agent_id",
  "workflow_id",
  "workflow_version_id",
  "trace_id",
  "request_id",
  "source",
] as const;
type RuntimeContextKey = (typeof runtimeContextKeys)[number];
type RuntimeTab = "overview" | "executions" | "diagnostics";

function queryValue(key: RuntimeContextKey) {
  const value = route.query[key];
  return typeof value === "string" && value ? value : undefined;
}

function hasRuntimeContext() {
  return runtimeContextKeys.some((key) => queryValue(key));
}

function routeTab(): RuntimeTab | undefined {
  const value = route.query.tab;
  return value === "overview" || value === "executions" || value === "diagnostics" ? value : undefined;
}

const activeTab = ref<RuntimeTab>(routeTab() || (hasRuntimeContext() ? "executions" : "overview"));
const executionsMounted = ref(activeTab.value === "executions");

const tabTitle = computed(() => activeTab.value === "overview" ? "运行健康" : activeTab.value === "executions" ? "Execution 运行中心" : "诊断路径");
const contextItems = computed(() => runtimeContextKeys
  .map((key) => ({ key, value: queryValue(key) }))
  .filter((item): item is { key: RuntimeContextKey; value: string } => Boolean(item.value)));

function routeQuery(extra: Record<string, string | undefined> = {}) {
  const query: Record<string, string> = {};
  for (const key of runtimeContextKeys) {
    const value = queryValue(key);
    if (value) query[key] = value;
  }
  const nextTab = extra.tab;
  if (nextTab) query.tab = nextTab;
  return query;
}

function selectTab(value: string | number) {
  const tab = String(value) as RuntimeTab;
  if (!["overview", "executions", "diagnostics"].includes(tab)) return;
  activeTab.value = tab;
  if (tab === "executions") executionsMounted.value = true;
  void router.replace({ path: "/runtime", query: routeQuery({ tab }) });
}

function syncRouteContext() {
  const nextTab = routeTab();
  if (nextTab) activeTab.value = nextTab;
  else if (hasRuntimeContext()) activeTab.value = "executions";
  if (activeTab.value === "executions" || hasRuntimeContext()) executionsMounted.value = true;
}

function openExecutions(status?: string) {
  executionsMounted.value = true;
  activeTab.value = "executions";
  void router.replace({
    path: "/runtime",
    query: routeQuery({ tab: "executions", ...(status ? { status } : {}) }),
  });
}

function openDiagnostics() {
  activeTab.value = "diagnostics";
  void router.replace({ path: "/runtime", query: routeQuery({ tab: "diagnostics" }) });
}

watch(() => route.query, syncRouteContext, { deep: true });
</script>

<template>
  <main class="runtime-workspace" aria-label="Runtime 可观测性工作台">
    <header class="workspace-heading">
      <div>
        <span class="eyebrow">P1.1 可观测性工作台</span>
        <h1>运行中心</h1>
        <p>从健康概览进入 Execution，再按需展开时间线、Trace、Audit 与 Workflow 关系。</p>
      </div>
      <div class="heading-context">
        <el-tag effect="plain">{{ tabTitle }}</el-tag>
        <el-tag v-if="contextItems.length" type="info" effect="plain">已携带 {{ contextItems.length }} 项上下文</el-tag>
      </div>
    </header>

    <el-tabs :model-value="activeTab" class="workspace-tabs" @update:model-value="selectTab">
      <el-tab-pane label="运行健康" name="overview">
        <RuntimeObservabilityOverview @open-runtime="openExecutions" />
      </el-tab-pane>
      <el-tab-pane label="Execution 运行中心" name="executions">
        <RuntimeExecutions v-if="executionsMounted" />
        <el-skeleton v-else :rows="6" animated />
      </el-tab-pane>
      <el-tab-pane label="诊断路径" name="diagnostics">
        <section class="diagnostic-card">
          <div class="diagnostic-title">企业级运行诊断闭环</div>
          <div v-if="contextItems.length" class="context-strip" aria-label="当前运行上下文">
            <span v-for="item in contextItems" :key="item.key" class="context-item">
              <b>{{ item.key }}</b>
              <code>{{ item.value }}</code>
            </span>
          </div>
          <div class="diagnostic-chain">
            <article><strong>01</strong><b>Execution</b><span>定位一次真实运行</span></article>
            <i>→</i>
            <article><strong>02</strong><b>Timeline</b><span>查看模型、工具、检索耗时</span></article>
            <i>→</i>
            <article><strong>03</strong><b>Trace</b><span>定位 Workflow 节点与错误</span></article>
            <i>→</i>
            <article><strong>04</strong><b>Audit</b><span>确认治理与操作记录</span></article>
          </div>
          <el-alert title="Runtime 详情采用按需加载：进入 Execution 后才请求时间线、Trace、Audit 与 Workflow 关系数据。" type="info" :closable="false" show-icon />
          <div class="diagnostic-actions">
            <el-button type="primary" plain @click="openExecutions()">进入 Execution 运行中心</el-button>
            <el-button text @click="openDiagnostics">刷新诊断上下文</el-button>
          </div>
        </section>
      </el-tab-pane>
    </el-tabs>
  </main>
</template>

<style scoped>
.runtime-workspace{padding:20px 32px}.workspace-heading{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;margin-bottom:4px}.eyebrow{font-size:10px;font-weight:700;letter-spacing:.08em;color:#667085}.workspace-heading h1{margin:4px 0;font-size:22px;color:#101828}.workspace-heading p{margin:0;color:#667085;font-size:12px}.heading-context{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}.workspace-tabs :deep(.el-tab-pane){padding-top:2px}.workspace-tabs :deep(.observability-panel){margin:8px 0 0}.diagnostic-card{padding:22px;border:1px solid #e4e7ed;border-radius:12px;background:#fff}.diagnostic-title{font-size:16px;font-weight:700;color:#1d2939}.context-strip{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0 0}.context-item{display:flex;align-items:center;gap:6px;padding:6px 8px;border:1px solid #eaecf0;border-radius:7px;background:#f8fafc}.context-item b{font-size:9px;color:#667085}.context-item code{max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:10px;color:#344054}.diagnostic-chain{display:flex;align-items:center;gap:10px;margin:20px 0}.diagnostic-chain article{flex:1;min-height:94px;padding:14px;border:1px solid #eaecf0;border-radius:10px;background:#fcfcfd}.diagnostic-chain strong,.diagnostic-chain b,.diagnostic-chain span{display:block}.diagnostic-chain strong{font-size:10px;color:#98a2b3}.diagnostic-chain b{margin:5px 0;color:#344054}.diagnostic-chain span{font-size:10px;color:#667085}.diagnostic-chain i{font-style:normal;color:#98a2b3}.diagnostic-actions{display:flex;gap:8px;margin-top:14px}@media(max-width:900px){.runtime-workspace{padding:14px}.workspace-heading{flex-direction:column}.heading-context{justify-content:flex-start}.diagnostic-chain{display:grid;grid-template-columns:1fr}.diagnostic-chain i{display:none}}@media(max-width:600px){.diagnostic-chain,.context-strip{grid-template-columns:1fr}.diagnostic-actions{flex-direction:column;align-items:flex-start}}
</style>
