<template>
  <div class="page">
    <PageHeader eyebrow="企业级智能体平台" title="平台工作台" description="统一查看智能体、工具和运行记录，快速进入治理与故障处理入口。"><template #actions><el-button :loading="loading" @click="load">刷新数据</el-button></template></PageHeader>
    <StatePanel v-if="pageState === 'permission'" state="permission" title="无权查看平台概览" description="当前账号缺少平台概览所需的数据访问权限，请联系管理员。" />
    <StatePanel v-else-if="pageState === 'error'" state="error" title="平台数据加载失败，请稍后重试" description="无法同步智能体、工具或运行记录，请检查服务状态后重试。" action-label="重试" @action="load" />
    <StatePanel v-else-if="pageState === 'loading'" state="loading" title="正在加载平台概览" description="正在同步智能体、工具和运行记录。" />
    <template v-if="pageState === 'empty'">
      <StatePanel state="empty" title="暂无平台运行数据" description="当前还没有智能体、工具或运行记录；创建并运行第一个资源后，这里会展示平台概览。" />
    </template>
    <template v-if="pageState === 'success' || pageState === 'empty'">
      <section class="metrics" v-loading="loading" aria-label="平台核心指标"><MetricCard v-for="metric in metricCards" :key="metric.key" :label="metric.label" :value="metric.value" :description="metric.description" :trend="metric.caption" trend-direction="neutral" /></section>
      <section class="workspace-grid">
        <SurfaceCard title="最近执行" description="最近 8 条运行记录"><template #header><el-button link type="primary" @click="$router.push('/runtime')">查看全部</el-button></template><div v-if="recentExecutions.length" class="activity-summary" aria-label="最近执行窗口摘要"><div><span>窗口记录</span><strong>{{ recentExecutions.length }}</strong></div><div><span>失败</span><strong>{{ recentFailedCount }}</strong></div><div><span>进行中</span><strong>{{ recentRunningCount }}</strong></div></div><el-table v-if="recentExecutions.length" :data="recentExecutions" size="small" show-overflow-tooltip><el-table-column label="执行" min-width="180"><template #default="{ row }"><code>{{ shortId(row.execution_id) }}</code></template></el-table-column><el-table-column prop="status" label="状态" width="110"><template #default="{ row }"><el-tag size="small" :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag></template></el-table-column><el-table-column prop="agent_id" label="智能体" min-width="150"><template #default="{ row }">{{ row.agent_id || "-" }}</template></el-table-column><el-table-column prop="duration_ms" label="耗时" width="100"><template #default="{ row }">{{ row.duration_ms != null ? `${row.duration_ms} 毫秒` : "-" }}</template></el-table-column><el-table-column label="开始时间" min-width="170"><template #default="{ row }">{{ formatTime(row.started_at) }}</template></el-table-column></el-table><el-empty v-else description="暂无运行记录" :image-size="72" /></SurfaceCard>
        <SurfaceCard title="常用入口" description="按业务职责快速进入"><button v-for="action in quickActions" :key="action.path" class="quick-action" type="button" @click="$router.push(action.path)"><span class="action-icon" aria-hidden="true">{{ action.icon }}</span><span class="action-copy"><strong>{{ action.label }}</strong><small>{{ action.description }}</small></span><span class="action-arrow" aria-hidden="true">→</span></button></SurfaceCard>
      </section>
      <section class="attention" v-if="metrics.failedExecutions > 0"><el-alert title="存在失败的运行记录" :description="`当前共有 ${metrics.failedExecutions} 次失败运行记录，建议进入运行记录查看执行链路与错误信息。`" type="warning" show-icon :closable="false"><template #default><el-button type="warning" link @click="$router.push('/runtime')">立即处理</el-button></template></el-alert></section>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import StatePanel from "@/components/ui/StatePanel.vue";
import MetricCard from "@/components/ui/MetricCard.vue";
import SurfaceCard from "@/components/ui/SurfaceCard.vue";
import { listAgents } from "@/api/agents";
import { listTools } from "@/api/tools";
import { runtimeApi, type Execution } from "@/api/runtime";
const loading = ref(false), error = ref(""), permissionDenied = ref(false), recentExecutions = ref<Execution[]>([]);
const metrics = reactive({ agents: 0, publishedAgents: 0, tools: 0, enabledTools: 0, executions: 0, failedExecutions: 0 });
const metricCards = computed(() => [
  { key: "agents", label: "智能体", value: metrics.agents, caption: `${metrics.publishedAgents} 个已发布`, description: "智能体生命周期资产" },
  { key: "published", label: "可运行智能体", value: metrics.publishedAgents, caption: "已发布", description: "当前可进入运行环境的智能体" },
  { key: "tools", label: "工具", value: `${metrics.enabledTools}/${metrics.tools}`, caption: "启用 / 总数", description: "工具治理与可用性" },
  { key: "executions", label: "运行记录", value: metrics.executions, caption: "累计执行", description: "系统运行记录总量" },
  { key: "failed", label: "失败运行", value: metrics.failedExecutions, caption: metrics.failedExecutions ? "需要关注" : "运行正常", description: "失败运行需要排查" },
]);
const pageState = computed(() => permissionDenied.value ? "permission" : error.value ? "error" : loading.value ? "loading" : metrics.agents + metrics.tools + metrics.executions === 0 ? "empty" : "success");
const recentFailedCount = computed(() => recentExecutions.value.filter((execution) => execution.status === "failed").length);
const recentRunningCount = computed(() => recentExecutions.value.filter((execution) => execution.status === "running" || execution.status === "pending").length);
const quickActions = [
  { path: "/agents", icon: "智", label: "智能体管理", description: "创建、版本、发布与对话调试" }, { path: "/tools", icon: "工", label: "工具管理", description: "查看工具能力与启用状态" }, { path: "/knowledge", icon: "知", label: "知识库", description: "管理知识资产与检索工作台" }, { path: "/workflows", icon: "流", label: "工作流", description: "编排、发布与运行工作流" }, { path: "/runtime", icon: "运", label: "运行记录", description: "检查运行记录、事件与链路" }, { path: "/runtime/audit", icon: "审", label: "审计日志", description: "追踪治理操作与运行审计" },
];
const executionStatusText: Record<string, string> = { completed: "已完成", succeeded: "成功", failed: "失败", running: "运行中", pending: "等待中", cancelled: "已取消", retrying: "重试中" };
async function load() { loading.value = true; error.value = ""; permissionDenied.value = false; try { const [agents, tools, executions, failed] = await Promise.all([listAgents(), listTools(), runtimeApi.executions({ page: 1, page_size: 8 }), runtimeApi.executions({ page: 1, page_size: 1, status: "failed" })]); metrics.agents = agents.length; metrics.publishedAgents = agents.filter((agent) => agent.status === "published").length; metrics.tools = tools.length; metrics.enabledTools = tools.filter((tool) => tool.enabled).length; metrics.executions = executions.data.total; metrics.failedExecutions = failed.data.total; recentExecutions.value = executions.data.items; } catch (e: any) { if (e?.response?.status === 403) permissionDenied.value = true; else error.value = "平台数据加载失败，请稍后重试"; } finally { loading.value = false; } }
function shortId(value?: string) { return value && value.length > 18 ? `${value.slice(0, 8)}...${value.slice(-6)}` : value || "-"; }
function formatTime(value?: string) { if (!value) return "-"; const date = new Date(value); return Number.isNaN(date.getTime()) ? "时间格式异常" : date.toLocaleString("zh-CN", { hour12: false }); }
function statusLabel(status: string) { return executionStatusText[status] || `未知状态（${status}）`; }
function statusType(status: string) { return status === "failed" ? "danger" : status === "completed" || status === "succeeded" ? "success" : status === "cancelled" ? "warning" : "info"; }
onMounted(load);
</script>

<style scoped>
.page { padding: var(--ui-space-8); max-width: 1480px; margin: 0 auto; }
.metrics { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:var(--ui-space-4); }
.workspace-grid { display:grid; grid-template-columns:minmax(0,1.7fr) minmax(320px,.9fr); gap:var(--ui-space-4); margin-top:var(--ui-space-4); }
.activity-summary { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; margin-bottom:12px; }
.activity-summary > div { padding:10px 12px; border:1px solid var(--ui-border-default); border-radius:var(--ui-radius-md); background:var(--ui-bg-subtle); }
.activity-summary span { display:block; color:var(--ui-text-tertiary); font-size:11px; }
.activity-summary strong { display:block; margin-top:3px; color:var(--ui-text-secondary); font-size:18px; line-height:1.1; }
code { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px; }
.quick-action { width:100%; border:0; border-bottom:1px solid var(--ui-border-subtle); background:transparent; padding:16px 4px; display:flex; align-items:center; gap:12px; text-align:left; cursor:pointer; }
.quick-action:last-child { border-bottom:0; }
.quick-action:hover { background:var(--ui-bg-subtle); }
.quick-action:focus-visible { outline:2px solid var(--ui-color-primary-500); outline-offset:-2px; border-radius:6px; }
.action-icon { width:36px; height:36px; display:grid; place-items:center; border-radius:9px; background:var(--ui-bg-muted); color:var(--ui-text-secondary); font-size:11px; font-weight:700; }
.action-copy { display:grid; gap:3px; flex:1; }
.action-copy strong { color:var(--ui-text-secondary); }
.action-copy small { color:var(--ui-text-tertiary); }
.action-arrow { color:var(--ui-text-tertiary); font-size:18px; }
.attention { margin-top:var(--ui-space-4); }
@media (max-width:1100px) { .metrics { grid-template-columns:repeat(3,minmax(0,1fr)); } .workspace-grid { grid-template-columns:1fr; } }
@media (max-width:700px) { .page { padding:var(--ui-space-5); } .metrics { grid-template-columns:repeat(2,minmax(0,1fr)); } .activity-summary { grid-template-columns:1fr; } }
@media (max-width:420px) { .metrics { grid-template-columns:1fr; } }
</style>
