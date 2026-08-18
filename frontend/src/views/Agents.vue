<template>
  <div class="page">
    <div class="header">
      <div>
        <h1>Agent 工作台</h1>
        <p>管理 Agent、版本并使用真实 SSE Runtime 调试。</p>
      </div>
      <el-button type="primary" @click="dialogVisible = true">创建 Agent</el-button>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon closable @close="error = ''" />
    <el-table v-loading="loadingAgents" :data="agents" border class="table">
      <el-table-column prop="name" label="名称" min-width="180" />
      <el-table-column prop="model_id" label="模型" width="160" />
      <el-table-column prop="version" label="版本" width="110" />
      <el-table-column prop="status" label="状态" width="110" />
      <el-table-column label="操作" width="260">
        <template #default="{ row }">
          <el-button link type="primary" @click="openVersions(row as Agent)">版本</el-button>
          <el-button link type="primary" @click="openChat(row as Agent)">调试 Chat</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loadingAgents && !agents.length" description="暂无 Agent，请先创建一个。" />

    <el-dialog v-model="dialogVisible" title="创建 Agent" width="560px">
      <el-form label-width="110px">
        <el-form-item label="名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" /></el-form-item>
        <el-form-item label="System Prompt" required><el-input v-model="form.system_prompt" type="textarea" :rows="5" /></el-form-item>
        <el-form-item label="模型" required><el-input v-model="form.model_id" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="create">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="versionsVisible" title="Agent Versions" width="720px">
      <el-table :data="versions" border>
        <el-table-column prop="version" label="版本" width="120" />
        <el-table-column prop="model_id" label="模型" width="160" />
        <el-table-column prop="created_at" label="创建时间" />
      </el-table>
      <el-divider />
      <el-form label-width="100px">
        <el-form-item label="System Prompt"><el-input v-model="versionForm.system_prompt" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="模型"><el-input v-model="versionForm.model_id" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="versionsVisible = false">关闭</el-button>
        <el-button type="primary" :loading="savingVersion" @click="createVersion">创建版本</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="chatVisible" :title="`调试：${selected?.name || ''}`" width="720px">
      <el-scrollbar height="360px" class="messages">
        <div v-for="(message, index) in messages" :key="index" :class="['message', message.role]">
          <b>{{ message.role === 'user' ? '你' : 'Agent' }}</b>
          <div>{{ message.content }}</div>
        </div>
        <el-empty v-if="!messages.length" description="输入消息开始调试" />
      </el-scrollbar>
      <el-input v-model="input" type="textarea" :rows="4" placeholder="输入消息..." @keyup.ctrl.enter="execute" />
      <div v-if="executionId" class="meta">Execution: {{ executionId }}</div>
      <template #footer>
        <el-button @click="chatVisible = false">关闭</el-button>
        <el-button type="primary" :loading="chatLoading" :disabled="!input.trim()" @click="execute">发送</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { createAgent, createVersion as createAgentVersion, listAgents, listVersions, type Agent, type AgentVersion } from "../api/agents";
import { streamChat } from "../api/chat";

const agents = ref<Agent[]>([]);
const versions = ref<AgentVersion[]>([]);
const loadingAgents = ref(false);
const saving = ref(false);
const savingVersion = ref(false);
const chatLoading = ref(false);
const dialogVisible = ref(false);
const versionsVisible = ref(false);
const chatVisible = ref(false);
const error = ref("");
const selected = ref<Agent | null>(null);
const input = ref("");
const executionId = ref("");
const sessionId = ref<string | undefined>();
const messages = ref<Array<{ role: string; content: string }>>([]);
const form = ref({ name: "企业智能助手", description: "", system_prompt: "你是一个企业级 AI 助手，请准确、简洁地回答用户问题。", model_id: "mock-model" });
const versionForm = ref({ system_prompt: "", model_id: "mock-model" });

async function load() {
  loadingAgents.value = true;
  error.value = "";
  try {
    agents.value = await listAgents();
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Agent 列表加载失败";
  } finally {
    loadingAgents.value = false;
  }
}

async function create() {
  saving.value = true;
  try {
    await createAgent(form.value);
    dialogVisible.value = false;
    await load();
    ElMessage.success("Agent 创建成功");
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : "Agent 创建失败");
  } finally {
    saving.value = false;
  }
}

async function openVersions(agent: Agent) {
  selected.value = agent;
  versionsVisible.value = true;
  versionForm.value = { system_prompt: "", model_id: agent.model_id || "mock-model" };
  try {
    versions.value = await listVersions(agent.id);
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : "版本加载失败");
  }
}

async function createVersion() {
  if (!selected.value || !versionForm.value.system_prompt.trim()) return;
  savingVersion.value = true;
  try {
    await createAgentVersion(selected.value.id, versionForm.value);
    versions.value = await listVersions(selected.value.id);
    await load();
    ElMessage.success("版本创建成功");
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : "版本创建失败");
  } finally {
    savingVersion.value = false;
  }
}

function openChat(agent: Agent) {
  selected.value = agent;
  input.value = "";
  sessionId.value = undefined;
  executionId.value = "";
  messages.value = [];
  chatVisible.value = true;
}

async function execute() {
  if (!selected.value || !input.value.trim() || chatLoading.value) return;
  const text = input.value.trim();
  input.value = "";
  messages.value.push({ role: "user", content: text });
  messages.value.push({ role: "assistant", content: "" });
  chatLoading.value = true;
  try {
    await streamChat({ agent_id: selected.value.id, input: text, session_id: sessionId.value, memory_limit: 20 }, (event) => {
      if (event.type === "start") sessionId.value = event.session_id;
      if (event.type === "delta") messages.value[messages.value.length - 1].content += event.content;
      if (event.type === "done") executionId.value = event.execution_id;
    });
  } catch (e) {
    messages.value[messages.value.length - 1].content = e instanceof Error ? e.message : "Chat 执行失败";
    ElMessage.error("Chat 执行失败");
  } finally {
    chatLoading.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.page { padding: 32px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.header p { color: #667085; }
.table { margin-top: 18px; }
.messages { margin-bottom: 16px; padding: 8px; background: #f8fafc; border-radius: 8px; }
.message { margin: 10px 0; padding: 10px 14px; border-radius: 8px; white-space: pre-wrap; }
.message.user { margin-left: 18%; background: #e8f3ff; }
.message.assistant { margin-right: 18%; background: #fff; }
.meta { margin-top: 10px; color: #667085; font-size: 12px; }
</style>
