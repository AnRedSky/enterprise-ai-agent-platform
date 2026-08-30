<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { runtimeApi, type Execution } from "@/api/runtime";
import { getRuntimeStatusMeta } from "@/utils/runtime";

const router = useRouter();
const loading = ref(false);
const executions = ref<Execution[]>([]);
const error = ref(false);

const counts = computed(() => executions.value.reduce((result, item) => {
  const status = item.status;
  result.total += 1;
  if (status === "failed") result.failed += 1;
  else if (["pending", "running", "retrying"].includes(status)) result.active += 1;
  else if (status === "completed") result.completed += 1;
  return result;
}, { total: 0, failed: 0, active: 0, completed: 0 }));

const healthLabel = computed(() => {
  if (counts.value.failed > 0) return "存在失败运行";
  if (counts.value.active > 0) return "运行中";
  return "运行稳定";
});

async function loadOverview() {
  loading.value = true;
  error.value = false;
  try {
    const response = await runtimeApi.executions({ page: 1, page_size: 20 });
    executions.value = response.data.items;
  } catch {
    error.value = true;
  } finally {
    loading.value = false;
  }
}

function openRuntime(status?: string) {
  void router.push({ path: "/runtime", query: status ? { status } : undefined });
}

onMounted(loadOverview);
</script>

<template>
  <section class="observability-panel" aria-label="运行可观测性概览">
    <div class="panel-heading">
      <div>
        <span class="eyebrow">P1 可观测性</span>
        <h2>运行健康概览</h2>
        <p>先判断运行健康，再进入 Execution、时间线、Trace 与 Audit 诊断。</p>
      </div>
      <div class="heading-actions">
        <el-tag :type="counts.failed ? 'danger' : 'success'" effect="plain">{{ healthLabel }}</el-tag>
        <el-button size="small" @click="loadOverview" :loading="loading">刷新概览</el-button>
      </div>
    </div>
    <el-alert v-if="error" title="运行健康概览暂时无法加载，请直接进入运行中心查看" type="warning" :closable="false" show-icon />
    <div v-else class="metric-grid">
      <button type="button" class="metric-card" @click="openRuntime()"><span>最近运行</span><strong>{{ counts.total }}</strong><small>最近 20 条 Execution</small></button>
      <button type="button" class="metric-card" @click="openRuntime('running')"><span>进行中</span><strong>{{ counts.active }}</strong><small>等待、运行与重试</small></button>
      <button type="button" class="metric-card" @click="openRuntime('completed')"><span>已完成</span><strong>{{ counts.completed }}</strong><small>成功结束的运行</small></button>
      <button type="button" class="metric-card danger" @click="openRuntime('failed')"><span>失败</span><strong>{{ counts.failed }}</strong><small>优先进入链路诊断</small></button>
    </div>
    <div class="diagnostic-flow">
      <span>Execution</span><i>→</i><span>时间线</span><i>→</i><span>Trace</span><i>→</i><span>Audit</span>
      <el-button link type="primary" @click="openRuntime()">进入运行中心</el-button>
    </div>
  </section>
</template>

<style scoped>
.observability-panel{margin:20px 32px 0;padding:20px 22px;border:1px solid #e4e7ed;border-radius:12px;background:#fff;box-shadow:0 2px 8px rgba(16,24,40,.03)}.panel-heading{display:flex;justify-content:space-between;gap:20px;align-items:flex-start}.eyebrow{font-size:10px;color:#667085;font-weight:700;letter-spacing:.08em}.panel-heading h2{margin:4px 0;font-size:17px;color:#1d2939}.panel-heading p{margin:0;color:#667085;font-size:12px}.heading-actions{display:flex;align-items:center;gap:10px}.metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:16px}.metric-card{padding:14px;text-align:left;border:1px solid #eaecf0;border-radius:9px;background:#fcfcfd;cursor:pointer}.metric-card:hover{border-color:#b8c7e6;transform:translateY(-1px)}.metric-card span,.metric-card small{display:block;color:#667085;font-size:11px}.metric-card strong{display:block;margin:4px 0;font-size:24px;color:#101828}.metric-card.danger strong{color:#b42318}.diagnostic-flow{display:flex;align-items:center;gap:9px;margin-top:14px;padding-top:12px;border-top:1px solid #f2f4f7;color:#475467;font-size:11px}.diagnostic-flow i{font-style:normal;color:#98a2b3}.diagnostic-flow .el-button{margin-left:auto}@media(max-width:800px){.observability-panel{margin:14px}.metric-grid{grid-template-columns:repeat(2,1fr)}.panel-heading{flex-direction:column}.heading-actions{width:100%}}
</style>
