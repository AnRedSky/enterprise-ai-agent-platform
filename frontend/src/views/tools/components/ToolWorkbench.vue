<template>
  <div class="page">
    <div class="header">
      <div>
        <h1>工具管理</h1>
        <p>
          管理工具的注册、启停、绑定、解绑和执行；创建及治理操作受管理员权限保护。
        </p>
      </div>
      <el-button v-if="isAdmin" type="primary" @click="createVisible = true"
        >创建工具</el-button
      >
    </div>
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      show-icon
      closable
      @close="error = ''"
    /><el-table v-loading="loading" :data="tools" border class="table"
      ><el-table-column
        prop="name"
        label="名称"
        min-width="180"
      /><el-table-column
        prop="description"
        label="描述"
        min-width="220"
      /><el-table-column label="状态" width="110"
        ><template #default="{ row }"
          ><el-tag :type="row.enabled ? 'success' : 'info'">{{
            row.enabled ? "启用" : "停用"
          }}</el-tag></template
        ></el-table-column
      ><el-table-column label="操作" width="420"
        ><template #default="{ row }"
          ><el-button
            v-if="isAdmin"
            link
            type="primary"
            @click="toggle(row as Tool)"
            >{{ row.enabled ? "停用" : "启用" }}</el-button
          ><el-button link type="primary" @click="openExecute(row as Tool)"
            >执行</el-button
          ><el-button
            v-if="isAdmin"
            link
            type="primary"
            @click="openBind(row as Tool, 'bind')"
            >绑定智能体</el-button
          ><el-button
            v-if="isAdmin"
            link
            type="danger"
            @click="openBind(row as Tool, 'unbind')"
            >解绑智能体</el-button
          ></template
        ></el-table-column
      ></el-table
    ><el-empty v-if="!loading && !tools.length" description="暂无可用工具。" />
    <el-dialog v-model="createVisible" title="创建工具" width="620px"
      ><el-form label-width="110px"
        ><el-form-item label="名称" required
          ><el-input v-model="createForm.name" /></el-form-item
        ><el-form-item label="描述"
          ><el-input v-model="createForm.description" /></el-form-item
        ><el-form-item label="接口地址"
          ><el-input
            v-model="createForm.endpoint"
            placeholder="可选；禁止执行未经授权的地址" /></el-form-item
        ><el-form-item label="输入结构"
          ><el-input
            v-model="createForm.input_schema"
            type="textarea"
            :rows="8" /></el-form-item></el-form
      ><template #footer
        ><el-button @click="createVisible = false">取消</el-button
        ><el-button type="primary" :loading="saving" @click="create"
          >创建</el-button
        ></template
      ></el-dialog
    >
    <el-dialog
      v-model="bindVisible"
      :title="
        bindingAction === 'bind' ? '绑定工具到智能体' : '解绑工具与智能体'
      "
      width="520px"
      ><el-select
        v-model="selectedAgent"
        placeholder="选择智能体"
        style="width: 100%"
        ><el-option
          v-for="agent in agents"
          :key="agent.id"
          :label="agent.name"
          :value="agent.id" /></el-select
      ><template #footer
        ><el-button @click="bindVisible = false">取消</el-button
        ><el-button
          :type="bindingAction === 'bind' ? 'primary' : 'danger'"
          :loading="saving"
          @click="applyBinding"
          >{{ bindingAction === "bind" ? "绑定" : "解绑" }}</el-button
        ></template
      ></el-dialog
    >
    <el-dialog
      v-model="executeVisible"
      :title="`执行工具：${selectedTool?.name || ''}`"
      width="620px"
      ><el-alert
        title="执行工具会创建运行记录，并受智能体与工具权限、启用状态及输入结构校验约束。"
        type="info"
        :closable="false"
      /><el-form label-width="110px" class="form"
        ><el-form-item label="智能体"
          ><el-select v-model="selectedAgent" style="width: 100%"
            ><el-option
              v-for="agent in agents"
              :key="agent.id"
              :label="agent.name"
              :value="agent.id" /></el-select></el-form-item
        ><el-form-item label="参数"
          ><el-input
            v-model="argumentsText"
            type="textarea"
            :rows="8" /></el-form-item></el-form
      ><el-alert
        v-if="executionResult"
        :title="executionResult"
        type="success"
        show-icon
      /><template #footer
        ><el-button @click="executeVisible = false">关闭</el-button
        ><el-button type="primary" :loading="executing" @click="execute"
          >执行</el-button
        ></template
      ></el-dialog
    >
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { getRoles } from "@/api/auth";
import { listAgents, type Agent } from "@/api/agents";
import {
  bindTool,
  createTool,
  disableTool,
  enableTool,
  executeTool,
  listTools,
  unbindTool,
  type Tool,
} from "@/api/tools";
type BindingAction = "bind" | "unbind";
const tools = ref<Tool[]>([]),
  agents = ref<Agent[]>([]),
  loading = ref(false),
  saving = ref(false),
  executing = ref(false),
  error = ref(""),
  createVisible = ref(false),
  bindVisible = ref(false),
  executeVisible = ref(false),
  selectedTool = ref<Tool | null>(null),
  selectedAgent = ref(""),
  bindingAction = ref<BindingAction>("bind"),
  argumentsText = ref("{}\n"),
  executionResult = ref(""),
  createForm = ref({
    name: "",
    description: "",
    endpoint: "",
    input_schema: "{}",
  });
const isAdmin = computed(() => getRoles().includes("admin"));
async function load() {
  loading.value = true;
  try {
    [tools.value, agents.value] = await Promise.all([
      listTools(),
      listAgents(),
    ]);
  } catch (e) {
    error.value = e instanceof Error ? e.message : "工具数据加载失败";
  } finally {
    loading.value = false;
  }
}
async function toggle(tool: Tool) {
  try {
    await (tool.enabled ? disableTool(tool.id) : enableTool(tool.id));
    await load();
    ElMessage.success(tool.enabled ? "工具已停用" : "工具已启用");
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : "工具状态更新失败");
  }
}
async function create() {
  try {
    const input_schema = JSON.parse(createForm.value.input_schema || "{}");
    saving.value = true;
    await createTool({ ...createForm.value, input_schema, enabled: true });
    createVisible.value = false;
    await load();
    ElMessage.success("工具创建成功");
  } catch (e) {
    ElMessage.error(
      e instanceof Error ? e.message : "工具创建失败，请检查输入结构是否正确",
    );
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
      ElMessage.success("工具绑定成功");
    } else {
      await unbindTool(selectedTool.value.id, selectedAgent.value);
      ElMessage.success("工具解绑成功");
    }
    bindVisible.value = false;
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : "工具绑定关系更新失败");
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
    ElMessage.warning("请选择智能体");
    return;
  }
  try {
    executing.value = true;
    const result = await executeTool(
      selectedTool.value.id,
      selectedAgent.value,
      JSON.parse(argumentsText.value || "{}"),
    );
    executionResult.value = JSON.stringify(result, null, 2);
  } catch (e) {
    executionResult.value = e instanceof Error ? e.message : "工具执行失败";
    ElMessage.error("工具执行失败");
  } finally {
    executing.value = false;
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
.table {
  margin-top: 18px;
}
.form {
  margin-top: 18px;
}
</style>
