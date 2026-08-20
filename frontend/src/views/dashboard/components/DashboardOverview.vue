<template>
  <div class="page">
    <div class="header">
      <div>
        <h1>企业级 AI Agent 平台</h1>
        <p>Phase 1.4 · Agent 生命周期、Runtime 与 Tool 治理总览</p>
      </div>
      <el-button :loading="loading" @click="load">刷新</el-button>
    </div>
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      :closable="false"
    />
    <div class="cards" v-loading="loading">
      <el-card
        ><template #header>Agent</template><b>{{ metrics.agents }}</b
        ><span>个 Agent</span></el-card
      ><el-card
        ><template #header>已发布</template><b>{{ metrics.publishedAgents }}</b
        ><span>个可运行 Agent</span></el-card
      ><el-card
        ><template #header>Tool</template
        ><b>{{ metrics.enabledTools }}/{{ metrics.tools }}</b
        ><span>启用 / 总数</span></el-card
      ><el-card
        ><template #header>Runtime</template><b>{{ metrics.executions }}</b
        ><span>次执行</span></el-card
      ><el-card
        ><template #header>失败执行</template
        ><b>{{ metrics.failedExecutions }}</b
        ><span>需要关注</span></el-card
      >
    </div>
    <div class="actions">
      <el-button type="primary" @click="$router.push('/agents')"
        >进入 Agent 管理</el-button
      ><el-button @click="$router.push('/tools')">进入 Tool 管理</el-button
      ><el-button @click="$router.push('/runtime')">查看 Runtime</el-button>
    </div>
  </div>
</template>
<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { listAgents } from "@/api/agents";
import { listTools } from "@/api/tools";
import { runtimeApi } from "@/api/runtime";
const loading = ref(false),
  error = ref(""),
  metrics = reactive({
    agents: 0,
    publishedAgents: 0,
    tools: 0,
    enabledTools: 0,
    executions: 0,
    failedExecutions: 0,
  });
async function load() {
  loading.value = true;
  error.value = "";
  try {
    const [agents, tools, executions, failed] = await Promise.all([
      listAgents(),
      listTools(),
      runtimeApi.executions({ page: 1, page_size: 1 }),
      runtimeApi.executions({ page: 1, page_size: 1, status: "failed" }),
    ]);
    metrics.agents = agents.length;
    metrics.publishedAgents = agents.filter(
      (agent) => agent.status === "published",
    ).length;
    metrics.tools = tools.length;
    metrics.enabledTools = tools.filter((tool) => tool.enabled).length;
    metrics.executions = executions.data.total;
    metrics.failedExecutions = failed.data.total;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Dashboard 数据加载失败";
    ElMessage.error("Dashboard 数据加载失败");
  } finally {
    loading.value = false;
  }
}
onMounted(load);
</script>
<style scoped>
.page {
  padding: 32px;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}
.header p {
  color: #667085;
}
.cards {
  display: grid;
  grid-template-columns: repeat(5, minmax(140px, 1fr));
  gap: 16px;
  margin: 28px 0;
}
.cards :deep(.el-card__header) {
  font-weight: 600;
}
.cards b {
  display: block;
  font-size: 30px;
  line-height: 1.3;
}
.cards span {
  color: #667085;
  font-size: 13px;
}
.actions {
  display: flex;
  gap: 12px;
}
@media (max-width: 1100px) {
  .cards {
    grid-template-columns: repeat(3, minmax(140px, 1fr));
  }
}
@media (max-width: 700px) {
  .cards {
    grid-template-columns: repeat(2, minmax(140px, 1fr));
  }
}
</style>
