<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { runtimeApi, type Execution } from "@/api/runtime";
import StatePanel from "@/components/ui/StatePanel.vue";

const router = useRouter();
const loading = ref(false);
const executions = ref<Execution[]>([]);
const error = ref(false);
const permissionDenied = ref(false);
const counts = computed(() => executions.value.reduce((result, item) => {
  result.total += 1;
  if (item.status === "failed") result.failed += 1;
  else if (["pending", "running", "retrying"].includes(item.status)) result.active += 1;
  else if (item.status === "completed") result.completed += 1;
  return result;
}, { total: 0, failed: 0, active: 0, completed: 0 }));
const healthLabel = computed(() => counts.value.failed > 0 ? "存在失败运行" : counts.value.active > 0 ? "运行中" : "运行稳定");
const state = computed(() => permissionDenied.value ? "permission" : error.value ? "error" : loading.value ? "loading" : executions.value.length === 0 ? "empty" : "success");
async function loadOverview() {
  loading.value = true; error.value = false; permissionDenied.value = false;
  try { const response = await runtimeApi.executions({ page: 1, page_size: 20 }); executions.value = response.data.items; }
  catch (e: any) { permissionDenied.value = e?.response?.status === 403; error.value = !permissionDenied.value; }
  finally { loading.value = false; }
}
function openRuntime(status?: string) { void router.push({ path: "/runtime", query: status ? { status } : undefined }); }
onMounted(loadOverview);
</script>

<template>
  <section class="observability-panel" aria-label="运行可观测性概览">
    <div class="panel-heading"><div><span class="eyebrow">P1 可观测性</span><h2>运行健康概览</h2><p>先判断运行健康，再进入 Execution、时间线、Trace 与 Audit 诊断。</p></div><div class="heading-actions"><el-tag :type="counts.failed ? 'danger' : 'success'" effect="plain">{{ healthLabel }}</el-tag><el-button size="small" @click="loadOverview" :loading="loading">刷新概览</el-button></div></div>
    <StatePanel v-if="state === 'loading'" state="loading" title="正在加载运行概览" description="正在同步最近 20 条 Execution。" />
    <StatePanel v-else-if="state === 'empty'" state="empty" title="暂无运行记录" description="当前没有可展示的 Execution，运行任务后会在这里出现。" action-label="进入运行中心" @action="openRuntime" />
    <StatePanel v-else-if="state === 'permission'" state="permission" title="无权查看运行概览" description="当前账号没有 Runtime 查询权限，请联系管理员授予相应访问权限。" />
    <StatePanel v-else-if="state === 'error'" state="error" title="运行概览加载失败" description="暂时无法获取运行数据，请检查服务状态后重试。" action-label="重试" @action="loadOverview" />
    <template v-else><div class="metric-grid"><button type="button" class="metric-card" @click="openRuntime()"><span>最近运行</span><strong>{{ counts.total }}</strong><small>最近 20 条 Execution</small></button><button type="button" class="metric-card" @click="openRuntime('running')"><span>进行中</span><strong>{{ counts.active }}</strong><small>等待、运行与重试</small></button><button type="button" class="metric-card" @click="openRuntime('completed')"><span>已完成</span><strong>{{ counts.completed }}</strong><small>成功结束的运行</small></button><button type="button" class="metric-card danger" @click="openRuntime('failed')"><span>失败</span><strong>{{ counts.failed }}</strong><small>优先进入链路诊断</small></button></div><div class="diagnostic-flow"><span>Execution</span><i>→</i><span>时间线</span><i>→</i><span>Trace</span><i>→</i><span>Audit</span><el-button link type="primary" @click="openRuntime()">进入运行中心</el-button></div></template>
  </section>
</template>

<style scoped>
.observability-panel{margin:20px 32px 0;padding:20px 22px;border:1px solid var(--ui-border-default);border-radius:var(--ui-radius-lg);background:var(--ui-bg-surface);box-shadow:var(--ui-shadow-sm)}.panel-heading{display:flex;justify-content:space-between;gap:20px;align-items:flex-start}.eyebrow{font-size:10px;color:var(--ui-text-tertiary);font-weight:700;letter-spacing:.08em}.panel-heading h2{margin:4px 0;font-size:17px;color:var(--ui-text-primary)}.panel-heading p{margin:0;color:var(--ui-text-tertiary);font-size:12px}.heading-actions{display:flex;align-items:center;gap:10px}.metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:16px}.metric-card{padding:14px;text-align:left;border:1px solid var(--ui-border-subtle);border-radius:var(--ui-radius-md);background:var(--ui-bg-subtle);cursor:pointer}.metric-card:hover{border-color:var(--ui-color-primary-300)}.metric-card span,.metric-card small{display:block;color:var(--ui-text-tertiary);font-size:11px}.metric-card strong{display:block;margin:4px 0;font-size:24px;color:var(--ui-text-primary)}.metric-card.danger strong{color:var(--ui-color-danger-500)}.diagnostic-flow{display:flex;align-items:center;gap:9px;margin-top:14px;padding-top:12px;border-top:1px solid var(--ui-border-subtle);color:var(--ui-text-secondary);font-size:11px}.diagnostic-flow i{font-style:normal;color:var(--ui-text-tertiary)}.diagnostic-flow .el-button{margin-left:auto}@media(max-width:800px){.observability-panel{margin:14px;padding:16px}.metric-grid{grid-template-columns:repeat(2,1fr)}.panel-heading{flex-direction:column}.heading-actions{width:100%}}@media(max-width:500px){.metric-grid{grid-template-columns:1fr}.diagnostic-flow{flex-wrap:wrap}.diagnostic-flow .el-button{margin-left:0;width:100%}}
</style>
