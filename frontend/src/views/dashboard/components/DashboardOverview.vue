<template>
  <div class="page">
    <section class="hero">
      <div>
        <p class="eyebrow">ENTERPRISE AI AGENT PLATFORM</p>
        <h1>平台工作台</h1>
        <p class="subtitle">统一查看 Agent、Tool 与 Runtime 运行态，快速进入治理和故障处理入口。</p>
      </div>
      <el-button :loading="loading" @click="load">刷新数据</el-button>
    </section>

    <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" class="error" />

    <section class="metrics" v-loading="loading">
      <el-card v-for="metric in metricCards" :key="metric.key" shadow="never" class="metric-card">
        <div class="metric-head">
          <span>{{ metric.label }}</span>
          <el-tag size="small" :type="metric.type">{{ metric.caption }}</el-tag>
        </div>
        <strong>{{ metric.value }}</strong>
        <span class="metric-description">{{ metric.description }}</span>
      </el-card>
    </section>

    <section class="workspace-grid">
      <el-card shadow="never" class="panel activity-panel">
        <template #header>
          <div class="panel-title">
            <div><strong>最近执行</strong><span>Runtime 最近 8 条执行记录</span></div>
            <el-button link type="primary" @click="$router.push('/runtime')">查看全部</el-button>
          </div>
        </template>
        <el-table v-if="recentExecutions.length" :data="recentExecutions" size="small">
          <el-table-column label="执行" min-width="180">
            <template #default="{ row }"><code>{{ shortId(row.execution_id) }}</code></template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="110">
            <template #default="{ row }"><el-tag size="small" :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag></template>
          </el-table-column>
          <el-table-column prop="agent_id" label="Agent" min-width="150"><template #default="{ row }">{{ row.agent_id || "-" }}</template></el-table-column>
          <el-table-column prop="duration_ms" label="耗时" width="100"><template #default="{ row }">{{ row.duration_ms != null ? `${row.duration_ms} ms` : "-" }}</template></el-table-column>
          <el-table-column label="开始时间" min-width="170"><template #default="{ row }">{{ formatTime(row.started_at) }}</template></el-table-column>
        </el-table>
        <el-empty v-else description="暂无 Runtime 执行记录" :image-size="72" />
      </el-card>

      <el-card shadow="never" class="panel actions-panel">
        <template #header><div class="panel-title"><div><strong>常用入口</strong><span>按业务职责快速进入</span></div></div></template>
        <button v-for="action in quickActions" :key="action.path" class="quick-action" @click="$router.push(action.path)">
          <span class="action-icon">{{ action.icon }}</span>
          <span class="action-copy"><strong>{{ action.label }}</strong><small>{{ action.description }}</small></span>
          <span class="action-arrow">→</span>
        </button>
      </el-card>
    </section>

    <section class="attention" v-if="metrics.failedExecutions > 0">
      <el-alert title="Runtime 存在失败执行" :description="`当前共有 ${metrics.failedExecutions} 次失败执行，建议进入 Runtime 查看执行链路与错误信息。`" type="warning" show-icon :closable="false">
        <template #default><el-button type="warning" link @click="$router.push('/runtime')">立即处理</el-button></template>
      </el-alert>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { listAgents } from "@/api/agents";
import { listTools } from "@/api/tools";
import { runtimeApi, type Execution } from "@/api/runtime";

const loading = ref(false);
const error = ref("");
const recentExecutions = ref<Execution[]>([]);
const metrics = reactive({ agents: 0, publishedAgents: 0, tools: 0, enabledTools: 0, executions: 0, failedExecutions: 0 });

const metricCards = computed(() => [
  { key: "agents", label: "Agent", value: metrics.agents, caption: `${metrics.publishedAgents} 个已发布`, description: "Agent 生命周期资产", type: "primary" as const },
  { key: "published", label: "可运行 Agent", value: metrics.publishedAgents, caption: "Published", description: "当前可进入 Runtime 的 Agent", type: "success" as const },
  { key: "tools", label: "Tool", value: `${metrics.enabledTools}/${metrics.tools}`, caption: "启用 / 总数", description: "Tool 治理与可用性", type: "info" as const },
  { key: "executions", label: "Runtime", value: metrics.executions, caption: "累计执行", description: "系统执行记录总量", type: "info" as const },
  { key: "failed", label: "失败执行", value: metrics.failedExecutions, caption: metrics.failedExecutions ? "需要关注" : "运行正常", description: "失败执行需要排查", type: metrics.failedExecutions ? "warning" as const : "success" as const },
]);

const quickActions = [
  { path: "/agents", icon: "AI", label: "Agent 管理", description: "创建、版本、发布与 Chat 调试" },
  { path: "/tools", icon: "TO", label: "Tool 管理", description: "查看工具能力与启用状态" },
  { path: "/knowledge", icon: "KB", label: "知识库", description: "管理知识资产与检索工作台" },
  { path: "/workflows", icon: "WF", label: "工作流", description: "编排、发布与执行工作流" },
  { path: "/runtime", icon: "RT", label: "Runtime", description: "检查执行、事件与 Trace" },
  { path: "/runtime/audit", icon: "AU", label: "审计日志", description: "追踪治理操作与执行审计" },
];

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const [agents, tools, executions, failed] = await Promise.all([
      listAgents(),
      listTools(),
      runtimeApi.executions({ page: 1, page_size: 8 }),
      runtimeApi.executions({ page: 1, page_size: 1, status: "failed" }),
    ]);
    metrics.agents = agents.length;
    metrics.publishedAgents = agents.filter((agent) => agent.status === "published").length;
    metrics.tools = tools.length;
    metrics.enabledTools = tools.filter((tool) => tool.enabled).length;
    metrics.executions = executions.data.total;
    metrics.failedExecutions = failed.data.total;
    recentExecutions.value = executions.data.items;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Dashboard 数据加载失败";
    ElMessage.error("Dashboard 数据加载失败");
  } finally {
    loading.value = false;
  }
}

function shortId(value?: string) { return value && value.length > 18 ? `${value.slice(0, 8)}...${value.slice(-6)}` : value || "-"; }
function formatTime(value?: string) { if (!value) return "-"; const date = new Date(value); return Number.isNaN(date.getTime()) ? value : date.toLocaleString("zh-CN", { hour12: false }); }
function statusLabel(status: string) { return ({ completed: "已完成", succeeded: "成功", failed: "失败", running: "运行中", pending: "等待中", cancelled: "已取消" } as Record<string, string>)[status] || status; }
function statusType(status: string) { return status === "failed" ? "danger" : status === "completed" || status === "succeeded" ? "success" : status === "cancelled" ? "warning" : "info"; }

onMounted(load);
</script>

<style scoped>
.page { padding: 30px 32px 40px; max-width: 1480px; margin: 0 auto; }
.hero { display: flex; justify-content: space-between; align-items: flex-end; gap: 24px; margin-bottom: 24px; }
.eyebrow { margin: 0 0 8px; font-size: 11px; letter-spacing: .12em; color: #98a2b3; font-weight: 700; }
h1 { margin: 0; font-size: 30px; line-height: 1.2; }
.subtitle { margin: 10px 0 0; color: #667085; }
.error { margin-bottom: 18px; }
.metrics { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 14px; }
.metric-card { min-height: 142px; border-radius: 12px; }
.metric-head { display: flex; justify-content: space-between; align-items: center; color: #667085; font-size: 13px; }
.metric-card strong { display: block; margin: 18px 0 4px; font-size: 30px; line-height: 1; color: #101828; }
.metric-description { color: #98a2b3; font-size: 12px; }
.workspace-grid { display: grid; grid-template-columns: minmax(0, 1.7fr) minmax(320px, .9fr); gap: 16px; margin-top: 16px; }
.panel { border-radius: 12px; min-height: 360px; }
.panel-title { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.panel-title > div { display: grid; gap: 3px; }
.panel-title span { color: #98a2b3; font-size: 12px; font-weight: 400; }
.activity-panel :deep(.el-card__body) { padding-top: 4px; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; }
.quick-action { width: 100%; border: 0; border-bottom: 1px solid #f2f4f7; background: transparent; padding: 16px 4px; display: flex; align-items: center; gap: 12px; text-align: left; cursor: pointer; }
.quick-action:last-child { border-bottom: 0; }
.quick-action:hover { background: #f8fafc; }
.action-icon { width: 36px; height: 36px; display: grid; place-items: center; border-radius: 9px; background: #f2f4f7; color: #344054; font-size: 11px; font-weight: 700; }
.action-copy { display: grid; gap: 3px; flex: 1; }
.action-copy strong { color: #344054; }
.action-copy small { color: #98a2b3; }
.action-arrow { color: #98a2b3; font-size: 18px; }
.attention { margin-top: 16px; }
.attention :deep(.el-alert__content) { width: 100%; }
@media (max-width: 1100px) { .metrics { grid-template-columns: repeat(3, minmax(0, 1fr)); } .workspace-grid { grid-template-columns: 1fr; } }
@media (max-width: 700px) { .page { padding: 20px 16px; } .hero { align-items: flex-start; flex-direction: column; } .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); } .metric-card { min-height: 125px; } }
</style>
