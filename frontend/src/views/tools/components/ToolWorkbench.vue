<template>
  <div class="page">
    <PageHeader
      title="工具管理"
      description="管理工具的注册、启停、绑定、解绑和执行；创建及治理操作受管理员权限保护。"
    >
      <template #actions>
        <el-button v-if="isAdmin" type="primary" @click="createVisible = true">创建工具</el-button>
      </template>
    </PageHeader>

    <StatePanel
      v-if="pageState !== 'success'"
      :state="pageState"
      :title="stateTitle"
      :description="stateDescription"
      :action-label="pageState === 'error' ? '重试' : pageState === 'empty' ? '创建工具' : undefined"
      @action="handleStateAction"
    />

    <template v-else>
      <PageToolbar title="工具列表" description="按启用状态和工具能力查看当前可用工具。">
        <span class="toolbar-count">共 {{ tools.length }} 个工具</span>
      </PageToolbar>

      <SurfaceCard>
        <el-table v-loading="loading" :data="tools" border class="table">
          <el-table-column prop="name" label="名称" min-width="180" />
          <el-table-column prop="description" label="描述" min-width="220" />
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="row.enabled ? 'success' : 'info'">
                {{ row.enabled ? "启用" : "停用" }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" min-width="420">
            <template #default="{ row }">
              <el-button v-if="isAdmin" link type="primary" @click="toggle(row as Tool)">
                {{ row.enabled ? "停用" : "启用" }}
              </el-button>
              <el-button link type="primary" @click="openExecute(row as Tool)">执行</el-button>
              <el-button v-if="isAdmin" link type="primary" @click="openBind(row as Tool, 'bind')">绑定智能体</el-button>
              <el-button v-if="isAdmin" link type="danger" @click="openBind(row as Tool, 'unbind')">解绑智能体</el-button>
            </template>
          </el-table-column>
        </el-table>
      </SurfaceCard>
    </template>

    <el-dialog v-model="createVisible" title="创建工具" width="620px">
      <el-form label-width="110px">
        <el-form-item label="名称" required><el-input v-model="createForm.name" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="createForm.description" /></el-form-item>
        <el-form-item label="接口地址">
          <el-input v-model="createForm.endpoint" placeholder="可选；禁止执行未经授权的地址" />
        </el-form-item>
        <el-form-item label="输入结构"><el-input v-model="createForm.input_schema" type="textarea" :rows="8" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="create">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="bindVisible"
      :title="bindingAction === 'bind' ? '绑定工具到智能体' : '解绑工具与智能体'"
      width="520px"
    >
      <el-select v-model="selectedAgent" placeholder="选择智能体" style="width: 100%">
        <el-option v-for="agent in agents" :key="agent.id" :label="agent.name" :value="agent.id" />
      </el-select>
      <template #footer>
        <el-button @click="bindVisible = false">取消</el-button>
        <el-button
          :type="bindingAction === 'bind' ? 'primary' : 'danger'"
          :loading="saving"
          @click="applyBinding"
        >{{ bindingAction === "bind" ? "绑定" : "解绑" }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="executeVisible" :title="`执行工具：${selectedTool?.name || ''}`" width="620px">
      <el-alert
        title="执行工具会创建运行记录，并受智能体与工具权限、启用状态及输入结构校验约束。"
        type="info"
        :closable="false"
      />
      <el-form label-width="110px" class="form">
        <el-form-item label="智能体">
          <el-select v-model="selectedAgent" style="width: 100%">
            <el-option v-for="agent in agents" :key="agent.id" :label="agent.name" :value="agent.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="参数"><el-input v-model="argumentsText" type="textarea" :rows="8" /></el-form-item>
      </el-form>
      <el-alert v-if="executionResult" :title="executionResult" type="success" show-icon />
      <template #footer>
        <el-button @click="executeVisible = false">关闭</el-button>
        <el-button type="primary" :loading="executing" @click="execute">执行</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import PageHeader from "@/components/ui/PageHeader.vue";
import PageToolbar from "@/components/ui/PageToolbar.vue";
import SurfaceCard from "@/components/ui/SurfaceCard.vue";
import StatePanel from "@/components/ui/StatePanel.vue";
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
import { getToolUserError } from "@/utils/toolError";

type BindingAction = "bind" | "unbind";
const tools = ref<Tool[]>([]), agents = ref<Agent[]>([]), loading = ref(false), saving = ref(false), executing = ref(false), error = ref("");
const permissionDenied = ref(false);
const createVisible = ref(false), bindVisible = ref(false), executeVisible = ref(false);
const selectedTool = ref<Tool | null>(null), selectedAgent = ref(""), bindingAction = ref<BindingAction>("bind");
const argumentsText = ref("{}\n"), executionResult = ref("");
const createForm = ref({ name: "", description: "", endpoint: "", input_schema: "{}" });
const isAdmin = computed(() => getRoles().includes("admin"));

const pageState = computed(() => permissionDenied.value ? "permission" : error.value ? "error" : loading.value ? "loading" : tools.value.length === 0 ? "empty" : "success");
const stateTitle = computed(() => {
  const titles: Record<string, string> = { loading: "正在加载工具", empty: "暂无可用工具", permission: "无权查看工具", error: "工具加载失败" };
  return titles[pageState.value] ?? "工具";
});
const stateDescription = computed(() => {
  const descriptions: Record<string, string> = { loading: "正在同步工具与智能体数据。", empty: "当前没有可用工具，请创建工具或启用已有工具。", permission: "当前账号没有工具访问权限，请联系管理员。", error: "无法同步工具与智能体数据，请检查服务状态后重试。" };
  return descriptions[pageState.value] ?? "";
});

async function load() {
  loading.value = true;
  error.value = "";
  permissionDenied.value = false;
  try {
    [tools.value, agents.value] = await Promise.all([listTools(), listAgents()]);
  } catch (e: any) {
    console.error(e);
    permissionDenied.value = e?.response?.status === 403;
    error.value = permissionDenied.value ? "" : getToolUserError(e, "工具数据加载失败，请稍后重试");
  } finally {
    loading.value = false;
  }
}

async function handleStateAction() {
  if (pageState.value === "empty") {
    createVisible.value = true;
    return;
  }
  if (pageState.value === "error") await load();
}

async function toggle(tool: Tool) {
  try {
    await (tool.enabled ? disableTool(tool.id) : enableTool(tool.id));
    await load();
    ElMessage.success(tool.enabled ? "工具已停用" : "工具已启用");
  } catch (e) {
    console.error(e);
    ElMessage.error(getToolUserError(e, "工具状态更新失败，请稍后重试"));
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
    console.error(e);
    ElMessage.error(getToolUserError(e, "工具创建失败，请稍后重试"));
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
    console.error(e);
    ElMessage.error(getToolUserError(e, "工具绑定关系更新失败，请稍后重试"));
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
    const result = await executeTool(selectedTool.value.id, selectedAgent.value, JSON.parse(argumentsText.value || "{}"));
    executionResult.value = JSON.stringify(result, null, 2);
  } catch (e) {
    console.error(e);
    executionResult.value = getToolUserError(e, "工具执行失败，请稍后重试");
    ElMessage.error("工具执行失败，请稍后重试");
  } finally {
    executing.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.page { padding: var(--ui-space-8); }
.toolbar-count { color: var(--ui-text-tertiary); font-size: 12px; white-space: nowrap; }
.table { width: 100%; }
.form { margin-top: 18px; }
@media (max-width: 700px) {
  .page { padding: var(--ui-space-5); }
  .toolbar-count { width: 100%; }
}
</style>
