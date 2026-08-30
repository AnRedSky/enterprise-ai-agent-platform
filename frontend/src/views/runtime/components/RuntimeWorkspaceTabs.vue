<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import RuntimeExecutions from "./RuntimeExecutions.vue";
import RuntimeObservabilityOverview from "./RuntimeObservabilityOverview.vue";

const route = useRoute();
const router = useRouter();
const activeTab = ref(typeof route.query.execution_id === "string" || typeof route.query.status === "string" ? "executions" : "overview");
const executionsMounted = ref(activeTab.value === "executions");

const tabTitle = computed(() => activeTab.value === "overview" ? "运行健康" : activeTab.value === "executions" ? "Execution 运行中心" : "诊断路径");

function selectTab(value: string) {
  activeTab.value = value;
  if (value === "executions") executionsMounted.value = true;
}

function openExecutions(status?: string) {
  executionsMounted.value = true;
  activeTab.value = "executions";
  void router.replace({ path: "/runtime", query: status ? { status } : undefined });
}
</script>

<template>
  <main class="runtime-workspace" aria-label="Runtime 可观测性工作台">
    <header class="workspace-heading">
      <div>
        <span class="eyebrow">P1.1 可观测性工作台</span>
        <h1>运行中心</h1>
        <p>从健康概览进入 Execution，再按需展开时间线、Trace、Audit 与恢复关系。</p>
      </div>
      <el-tag effect="plain">{{ tabTitle }}</el-tag>
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
          <el-button type="primary" plain @click="openExecutions()">进入 Execution 运行中心</el-button>
        </section>
      </el-tab-pane>
    </el-tabs>
  </main>
</template>

<style scoped>
.runtime-workspace{padding:20px 32px}.workspace-heading{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;margin-bottom:4px}.eyebrow{font-size:10px;font-weight:700;letter-spacing:.08em;color:#667085}.workspace-heading h1{margin:4px 0;font-size:22px;color:#101828}.workspace-heading p{margin:0;color:#667085;font-size:12px}.workspace-tabs :deep(.el-tab-pane){padding-top:2px}.workspace-tabs :deep(.observability-panel){margin:8px 0 0}.diagnostic-card{padding:22px;border:1px solid #e4e7ed;border-radius:12px;background:#fff}.diagnostic-title{font-size:16px;font-weight:700;color:#1d2939}.diagnostic-chain{display:flex;align-items:center;gap:10px;margin:20px 0}.diagnostic-chain article{flex:1;min-height:94px;padding:14px;border:1px solid #eaecf0;border-radius:10px;background:#fcfcfd}.diagnostic-chain strong,.diagnostic-chain b,.diagnostic-chain span{display:block}.diagnostic-chain strong{font-size:10px;color:#98a2b3}.diagnostic-chain b{margin:5px 0;color:#344054}.diagnostic-chain span{font-size:10px;color:#667085}.diagnostic-chain i{font-style:normal;color:#98a2b3}.diagnostic-card .el-button{margin-top:14px}@media(max-width:900px){.runtime-workspace{padding:14px}.workspace-heading{flex-direction:column}.diagnostic-chain{display:grid;grid-template-columns:1fr}.diagnostic-chain i{display:none}}
</style>
