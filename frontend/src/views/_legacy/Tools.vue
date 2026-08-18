<template>
  <div class="page">
    <div class="header">
      <div><h1>Tool 管理</h1><p>工具注册、启停、绑定/解绑与执行；创建和治理操作受管理员 RBAC 保护。</p></div>
      <el-button v-if="isAdmin" type="primary" @click="createVisible = true">创建 Tool</el-button>
    </div>

    <el-alert v-if="error" :title="error" type="error" show-icon closable @close="error = ''" />
    <el-table v-loading="loading" :data="tools" border class="table">
      <el-table-column prop="name" label="名称" min-width="180" />
      <el-table-column prop="description" label="描述" min-width="220" />
      <el-table-column label="状态" width="110"><template #default="{ row }"><el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '启用' : '停用' }}</el-tag></template></el-table-column>
      <el-table-column label="操作" width="420">
        <template #default="{ row }">
          <el-button v-if="isAdmin" link type="primary" @click="toggle(row as Tool)">{{ row.enabled ? '停用' : '启用' }}</el-button>
          <el-button link type="primary" @click="openExecute(row as Tool)">执行</el-button>
          <el-button v-if="isAdmin" link type="primary" @click="openBind(row as Tool, 'bind')">绑定 Agent</el-button>
          <el-button v-if="isAdmin" link type="danger" @click="openBind(row as Tool, 'unbind')">解绑 Agent</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && !tools.length" description="暂无可用 Tool。" />

    <el-dialog v-model="createVisible" title="创建 Tool" width="620px">
      <el-form label-width="110px">
        <el-form-item label="名称" required><el-input v-model="createForm.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="createForm.description" /></el-form-item>
        <el-form-item label="Endpoint"><el-input v-model="createForm.endpoint" placeholder="可选；禁止未经授权的 URL 执行" /></el-form-item>
        <el-form-item label="Input Schema"><el-input v-model="createForm.input_schema" type="textarea" :rows="8" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="createVisible = false">取消</el-button><el-button type="primary" :loading="saving" @click="create">创建</el-button></template>
    </el-dialog>

    <el-dialog v-model="bindVisible" :title="bindingAction === 'bind' ? '绑定 Tool 到 Agent' : '解绑 Tool 到 Agent'" width="520px">
      <el-select v-model="selectedAgent" placeholder="选择 Agent" style="width: 100%">
        <el-option v-for="agent in agents" :key="agent.id" :label="agent.name" :value="agent.id" />
      </el-select>
      <template #footer><el-button @click="bindVisible = false">取消</el-button><el-button :type="bindingAction === 'bind' ? 'primary' : 'danger'" :loading="saving" @click="applyBinding">{{ bindingAction === 'bind' ? '绑定' : '解绑' }}</el-button></template>
    </el-dialog>

    <el-dialog v-model="executeVisible" :title="`执行 Tool：${selectedTool?.name || ''}`" width="620px">
      <el-alert title="Tool Execute 会创建 Runtime Execution，并受 Agent/Tool 权限、启用状态和 Schema 校验约束。" type="info" :closable="false" />
      <el-form label-width="110px" class="form">
        <el-form-item label="Agent"><el-select v-model="selectedAgent" style="width: 100%"><el-option v-for="agent in agents" :key="agent.id" :label="agent.name" :value="agent.id" /></el-select></el-form-item>
        <el-form-item label="Arguments"><el-input v-model="argumentsText" type="textarea" :rows="8" /></el-form-item>
      </el-form>
      <el-alert v-if="executionResult" :title="executionResult" type="success" show-icon />
      <template #footer><el-button @click="executeVisible = false">关闭</el-button><el-button type="primary" :loading="executing" @click="execute">执行</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { getRoles } from "../api/auth";
import { listAgents, type Agent } from "../api/agents";
import { bindTool, createTool, disableTool, enableTool, executeTool, listTools, unbindTool, type Tool } from "../api/tools";

type BindingAction = "bind" | "unbind";
const tools = ref<Tool[]>([]);
const agents = ref<Agent[]>([]);
const loading = ref(false);
const saving = ref(false);
const executing = ref(false);
const error = ref("");
const createVisible = ref(false);
const bindVisible = ref(false);
const executeVisible = ref(false);
const selectedTool = ref<Tool | null>(null);
const selectedAgent = ref("");
const bindingAction = ref<BindingAction>("bind");
const argumentsText = ref("{}\n");
const executionResult = ref("");
const createForm = ref({ name: "", description: "", endpoint: "", input_schema: "{}" });
const isAdmin = computed(() => getRoles().includes("admin"));

async function load() {
  loading.value = true;
  try {
    [tools.value, agents.value] = await Promise.all([listTools(), listAgents()]);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "Tool 数据加载失败";
  } finally {
    loading.value = false;
  }
}

async function toggle(tool: Tool) {
  try {
    await (tool.enabled ? disableTool(tool.id) : enableTool(tool.id));
    await load();
    ElMessage.success(tool.enabled ? "Tool 已停用" : "Tool 已启用");
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : "Tool 状态更新失败");
  }
}

async function create() {
  try {
    const input_schema = JSON.parse(createForm.value.input_schema || "{}");
    saving.value = true;
    await createTool({ ...createForm.value, input_schema, enabled: true });
    createVisible.value = false;
    await load();
    ElMessage.success("Tool 创建成功");
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : "Tool 创建失败，请检查 JSON Schema");
  } finally {
    saving.value = false;
  }
}

function openBind(tool: Tool, action: BindingAction) {
  selectedTool.value = tool;
  bindingAction.value = action;
  selectedAgent.value = agents.value[0]?.id || "";
  bindVisible.value = true;
}

async function applyBinding() {
  if (!selectedTool.value || !selectedAgent.value) return;
  saving.value = true;
  try {
    if (bindingAction.value === "bind") {
      await bindTool(selectedTool.value.id, selectedAgent.value);
      ElMessage.success("Tool 绑定成功");
    } else {
      await unbindTool(selectedTool.value.id, selectedAgent.value);
      ElMessage.success("Tool 解绑成功");
    }
    bindVisible.value = false;
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : "Tool 绑定关系更新失败");
  } finally {
    saving.value = false;
  }
}

function openExecute(tool: Tool) {
  selectedTool.value = tool;
  selectedAgent.value = agents.value[0]?.id || "";
  argumentsText.value = "{}\n";
  executionResult.value = "";
  executeVisible.value = true;
}

async function execute() {
  if (!selectedTool.value || !selectedAgent.value) {
    ElMessage.warning("请选择 Agent");
    return;
  }
  try {
    executing.value = true;
    const result = await executeTool(selectedTool.value.id, selectedAgent.value, JSON.parse(argumentsText.value || "{}"));
    executionResult.value = JSON.stringify(result, null, 2);
  } catch (e) {
    executionResult.value = e instanceof Error ? e.message : "Tool 执行失败";
    ElMessage.error("Tool 执行失败");
  } finally {
    executing.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.page { padding: 32px; }
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.header p { color: #667085; }
.table { margin-top: 18px; }
.form { margin-top: 18px; }
</style>
