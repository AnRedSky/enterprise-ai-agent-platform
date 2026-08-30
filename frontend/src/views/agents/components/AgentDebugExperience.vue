<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { getPublishedVersion, listAgents, type Agent, type AgentVersion } from "@/api/agents";
const router = useRouter(); const expanded = ref(true); const loading = ref(false); const error = ref(false); const agents = ref<Agent[]>([]); const selectedAgentId = ref(""); const publishedVersion = ref<AgentVersion | null>(null);
const selectedAgent = computed(() => agents.value.find((item) => item.id === selectedAgentId.value) || null);
const checks = computed(() => [
  { label: "已发布版本", done: !!publishedVersion.value, description: publishedVersion.value ? `当前生效版本：${publishedVersion.value.version}` : "选择智能体后读取真实发布版本" },
  { label: "运行上下文", done: !!publishedVersion.value, description: "请求、会话、执行与链路标识会随调试过程保留" },
  { label: "失败可诊断", done: !!selectedAgent.value, description: "失败后可直接进入运行中心查看 Trace 与 Audit" },
]);
async function loadDebugContext() { loading.value = true; error.value = false; try { agents.value = await listAgents(); selectedAgentId.value = agents.value[0]?.id || ""; if (selectedAgentId.value) publishedVersion.value = await getPublishedVersion(selectedAgentId.value); } catch (err) { console.error("智能体调试上下文加载失败", err); error.value = true; } finally { loading.value = false; } }
async function selectAgent(id: string) { selectedAgentId.value = id; publishedVersion.value = null; if (!id) return; try { publishedVersion.value = await getPublishedVersion(id); } catch (err) { console.error("智能体生效版本加载失败", err); ElMessage.error("智能体生效版本加载失败，请刷新后重试"); } }
function openRuntime() { void router.push({ path: "/runtime", query: { source: "agent-debug", ...(selectedAgentId.value ? { agent_id: selectedAgentId.value } : {}) } }); }
onMounted(loadDebugContext);
</script>
<template>
  <section class="debug-panel" aria-label="智能体对话调试体验">
    <div class="debug-head"><div><span class="eyebrow">P1.1 对话调试</span><h2>对话调试上下文</h2><p>把发布版本、系统提示词与运行标识放进同一调试上下文，失败后可直接进入 Runtime 诊断。</p></div><div class="actions"><el-tag :type="publishedVersion ? 'success' : 'warning'" effect="plain">{{ publishedVersion ? "可调试" : "等待发布版本" }}</el-tag><el-button text @click="expanded = !expanded">{{ expanded ? "收起" : "展开" }}</el-button></div></div>
    <el-alert v-if="error" title="智能体调试上下文加载失败，请刷新后重试" type="warning" :closable="false" show-icon />
    <div v-if="expanded" class="debug-body">
      <div class="context-grid"><div class="context-field"><span>调试智能体</span><el-select :model-value="selectedAgentId" placeholder="选择智能体" :loading="loading" @update:model-value="selectAgent"><el-option v-for="agent in agents" :key="agent.id" :label="agent.name" :value="agent.id" /></el-select></div><div class="context-field"><span>当前生效版本</span><strong>{{ publishedVersion?.version || "-" }}</strong></div><div class="context-field"><span>版本标识</span><code>{{ publishedVersion?.id || "-" }}</code></div><div class="context-field"><span>模型</span><strong>{{ publishedVersion?.model_id || selectedAgent?.model_id || "-" }}</strong></div></div>
      <div class="prompt-card"><span>系统提示词</span><p>{{ publishedVersion?.system_prompt || "发布版本加载后显示系统提示词摘要" }}</p></div>
      <div class="check-list"><div v-for="item in checks" :key="item.label" class="check-item"><span :class="['check-mark', { pending: !item.done }]">{{ item.done ? "✓" : "·" }}</span><div><strong>{{ item.label }}</strong><small>{{ item.description }}</small></div></div></div>
      <div class="debug-route"><div><strong>对话调试 → 运行中心</strong><span>请求标识 / 会话标识 / Trace / Execution / Audit</span></div><el-button type="primary" plain size="small" @click="openRuntime">查看运行中心</el-button></div>
    </div>
  </section>
</template>
<style scoped>
.debug-panel{margin:20px 32px 0;padding:18px 22px;border:1px solid #e4e7ed;border-radius:12px;background:#fff}.debug-head{display:flex;justify-content:space-between;gap:20px}.eyebrow{font-size:10px;color:#667085;font-weight:700;letter-spacing:.08em}.debug-head h2{margin:4px 0;font-size:17px;color:#1d2939}.debug-head p{margin:0;color:#667085;font-size:12px}.actions{display:flex;align-items:flex-start;gap:8px}.debug-body{margin-top:16px}.context-grid{display:grid;grid-template-columns:1.5fr 1fr 1.5fr 1fr;gap:10px}.context-field{padding:11px;border:1px solid #eaecf0;border-radius:9px;background:#fcfcfd}.context-field>span,.context-field>strong,.context-field>code{display:block}.context-field>span{font-size:10px;color:#667085}.context-field>strong,.context-field>code{margin-top:5px;font-size:12px;color:#344054}.context-field code{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.context-field :deep(.el-select){width:100%;margin-top:5px}.prompt-card{margin-top:10px;padding:12px 14px;border:1px solid #eaecf0;border-radius:9px}.prompt-card span{font-size:10px;color:#667085}.prompt-card p{margin:6px 0 0;color:#344054;font-size:11px;line-height:1.6;max-height:54px;overflow:auto;white-space:pre-wrap}.check-list{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:10px}.check-item{display:flex;gap:9px;padding:12px;border:1px solid #eaecf0;border-radius:9px;background:#fcfcfd}.check-mark{display:grid;place-items:center;width:20px;height:20px;border-radius:50%;background:#ecfdf3;color:#027a48;font-size:11px}.check-mark.pending{background:#fef3f2;color:#b42318}.check-item strong,.check-item small{display:block}.check-item strong{font-size:12px;color:#344054}.check-item small{margin-top:3px;color:#667085;font-size:10px;line-height:1.5}.debug-route{display:flex;justify-content:space-between;align-items:center;margin-top:10px;padding:12px 14px;border-radius:9px;background:#f8fafc}.debug-route strong,.debug-route span{display:block}.debug-route strong{font-size:12px;color:#344054}.debug-route span{margin-top:3px;color:#667085;font-size:10px}@media(max-width:900px){.debug-panel{margin:14px}.debug-head{flex-direction:column}.context-grid,.check-list{grid-template-columns:1fr 1fr}}@media(max-width:600px){.context-grid,.check-list{grid-template-columns:1fr}.debug-route{align-items:flex-start;gap:10px;flex-direction:column}}
</style>
