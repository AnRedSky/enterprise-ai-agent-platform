<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { workflowApi, type Workflow, type WorkflowExecution, type WorkflowExecutionNode, type WorkflowVersion, type WorkflowTrace } from "@/api/workflows";

const workflows = ref<Workflow[]>([]);
const versions = ref<WorkflowVersion[]>([]);
const selected = ref<Workflow>();
const selectedVersion = ref<WorkflowVersion>();
const execution = ref<WorkflowExecution>();
const executionNodes = ref<WorkflowExecutionNode[]>([]);
const traces = ref<WorkflowTrace[]>([]);
const audits = ref<Array<Record<string, unknown>>>([]);
const loading = ref(false);
const auditLoading = ref(false);
const executionLoading = ref(false);
const executionActionLoading = ref(false);
const form = ref({ name: "", description: "" });
const definitionText = ref('{\n  "nodes": [],\n  "edges": []\n}');
const executionInputText = ref("{}");
const executionId = ref("");
const traceExecutionId = ref("");

async function load() {
  loading.value = true;
  try { workflows.value = (await workflowApi.list()).data; }
  catch { ElMessage.error("Workflow 查询失败"); }
  finally { loading.value = false; }
}

async function selectWorkflow(row: Workflow) {
  selected.value = row;
  selectedVersion.value = undefined;
  execution.value = undefined;
  executionNodes.value = [];
  traces.value = [];
  try { versions.value = (await workflowApi.versions(row.id)).data; }
  catch { ElMessage.error("Workflow Version 查询失败"); }
}

async function createWorkflow() {
  if (!form.value.name.trim()) return ElMessage.warning("请输入 Workflow 名称");
  try {
    const created = (await workflowApi.create(form.value)).data;
    ElMessage.success("Workflow 创建成功");
    form.value = { name: "", description: "" };
    await load();
    await selectWorkflow(created);
  } catch { ElMessage.error("Workflow 创建失败"); }
}

async function saveVersion() {
  if (!selected.value) return;
  try {
    const definition = JSON.parse(definitionText.value) as Record<string, unknown>;
    const version = (await workflowApi.createVersion(selected.value.id, definition)).data;
    ElMessage.success(`Version ${version.version} 创建成功`);
    await selectWorkflow(selected.value);
    selectedVersion.value = version;
  } catch (error) {
    ElMessage.error(error instanceof SyntaxError ? "Workflow Definition 不是合法 JSON" : "Version 创建失败");
  }
}

async function publishVersion(version: WorkflowVersion) {
  if (!selected.value) return;
  try {
    await ElMessageBox.confirm(`确认发布 Version ${version.version}？`, "发布 Workflow", { type: "warning" });
    await workflowApi.publish(selected.value.id, version.id);
    ElMessage.success("Workflow Version 发布成功");
    await load();
    await selectWorkflow(selected.value);
  } catch (error) {
    if (error !== "cancel") ElMessage.error("Workflow Version 发布失败");
  }
}

async function createExecution() {
  if (!selected.value?.published_version_id) return ElMessage.warning("请先发布 Workflow Version");
  try {
    const inputData = JSON.parse(executionInputText.value) as Record<string, unknown>;
    executionActionLoading.value = true;
    const response = await workflowApi.createExecution(selected.value.id, inputData);
    execution.value = response.data;
    executionId.value = response.data.id;
    executionNodes.value = [];
    ElMessage.success("Workflow Execution 创建成功");
  } catch (error) {
    ElMessage.error(error instanceof SyntaxError ? "Execution Input 不是合法 JSON" : "Workflow Execution 创建失败");
  } finally { executionActionLoading.value = false; }
}

async function runExecution() {
  const id = execution.value?.id || executionId.value.trim();
  if (!id) return ElMessage.warning("请先创建或输入 Workflow Execution ID");
  executionActionLoading.value = true;
  try {
    execution.value = (await workflowApi.runExecution(id)).data;
    executionId.value = id;
    const nodesResponse = await workflowApi.executionNodes(id);
    executionNodes.value = nodesResponse.data;
    ElMessage.success("Workflow Execution 已完成运行请求");
  } catch { ElMessage.error("Workflow Execution 运行失败"); }
  finally { executionActionLoading.value = false; }
}

async function cancelExecution() {
  if (!execution.value || !["pending", "running"].includes(execution.value.status)) return;
  try {
    const result = await ElMessageBox.prompt("可选：填写取消原因", "取消 Workflow Execution", {
      inputPlaceholder: "例如：业务方要求停止",
      confirmButtonText: "确认取消",
      cancelButtonText: "返回",
      inputValidator: (value) => value.length <= 500 || "取消原因不能超过 500 个字符",
      type: "warning",
    });
    executionActionLoading.value = true;
    execution.value = (await workflowApi.cancelExecution(execution.value.id, result.value)).data;
    await loadExecutionDetails(execution.value.id);
    ElMessage.success("Workflow Execution 已取消");
  } catch (error) {
    if (error !== "cancel" && error !== "close") ElMessage.error("Workflow Execution 取消失败");
  } finally { executionActionLoading.value = false; }
}

async function retryExecution() {
  if (!execution.value || execution.value.status !== "failed") return;
  try {
    await ElMessageBox.confirm("将基于原失败 Execution 的输入和版本创建新的 Execution，是否继续？", "Retry Workflow Execution", { type: "warning" });
    executionActionLoading.value = true;
    execution.value = (await workflowApi.retryExecution(execution.value.id)).data;
    executionId.value = execution.value.id;
    executionNodes.value = [];
    ElMessage.success("Retry Execution 已创建，可继续运行");
  } catch (error) {
    if (error !== "cancel") ElMessage.error("Retry Execution 创建失败");
  } finally { executionActionLoading.value = false; }
}

async function loadExecutionDetails(id: string) {
  const [executionResponse, nodesResponse] = await Promise.all([
    workflowApi.execution(id),
    workflowApi.executionNodes(id),
  ]);
  execution.value = executionResponse.data;
  executionNodes.value = nodesResponse.data;
  executionId.value = id;
}

async function loadExecution() {
  const id = executionId.value.trim();
  if (!id) return ElMessage.warning("请输入 Workflow Execution ID");
  executionLoading.value = true;
  try { await loadExecutionDetails(id); }
  catch { ElMessage.error("Workflow Execution 查询失败"); }
  finally { executionLoading.value = false; }
}

async function loadAudit() {
  if (!selected.value) return;
  auditLoading.value = true;
  try { audits.value = (await workflowApi.audit({ page: 1, page_size: 50, workflow_id: selected.value.id })).data.items; }
  catch { ElMessage.error("Audit 查询失败"); }
  finally { auditLoading.value = false; }
}

async function loadTrace() {
  if (!traceExecutionId.value.trim()) return ElMessage.warning("请输入 Workflow Execution ID");
  try { traces.value = (await workflowApi.trace(traceExecutionId.value.trim())).data.items; }
  catch { ElMessage.error("Trace 查询失败"); }
}

function useVersion(version: WorkflowVersion) {
  selectedVersion.value = version;
  definitionText.value = JSON.stringify(version.definition, null, 2);
}

onMounted(load);
</script>

<template>
  <div class="workflow-page">
    <el-row :gutter="16">
      <el-col :span="8">
        <el-card v-loading="loading">
          <template #header><div class="header"><span>Workflow Registry</span><el-button type="primary" size="small" @click="load">刷新</el-button></div></template>
          <el-form label-position="top" @submit.prevent="createWorkflow">
            <el-form-item label="名称"><el-input v-model="form.name" placeholder="企业流程名称" /></el-form-item>
            <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
            <el-button type="primary" native-type="submit">创建 Workflow</el-button>
          </el-form>
          <el-divider />
          <el-table :data="workflows" highlight-current-row @row-click="selectWorkflow">
            <el-table-column prop="name" label="Workflow" min-width="150" />
            <el-table-column prop="status" label="状态" width="90" />
            <el-table-column prop="updated_at" label="更新" min-width="170" />
          </el-table>
          <el-empty v-if="!workflows.length && !loading" description="暂无 Workflow" />
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card v-if="selected">
          <template #header><div class="header"><span>{{ selected.name }} / Governance</span><el-tag>{{ selected.status }}</el-tag></div></template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="Workflow ID">{{ selected.id }}</el-descriptions-item>
            <el-descriptions-item label="Published Version">{{ selected.published_version_id || '-' }}</el-descriptions-item>
            <el-descriptions-item label="Owner">{{ selected.owner_id }}</el-descriptions-item>
            <el-descriptions-item label="Updated">{{ selected.updated_at }}</el-descriptions-item>
          </el-descriptions>
          <el-tabs @tab-change="(name) => name === 'audit' && loadAudit()">
            <el-tab-pane label="Versions" name="versions">
              <el-table :data="versions" @row-click="useVersion">
                <el-table-column prop="version" label="Version" width="90" />
                <el-table-column prop="status" label="状态" width="110" />
                <el-table-column prop="created_at" label="Created" min-width="180" />
                <el-table-column label="操作" width="110">
                  <template #default="scope"><el-button size="small" type="success" @click.stop="publishVersion(scope.row as WorkflowVersion)">发布</el-button></template>
                </el-table-column>
              </el-table>
            </el-tab-pane>
            <el-tab-pane label="Definition" name="definition">
              <el-alert title="当前阶段使用 JSON Definition 合约；后续可替换为可视化 DAG 编排器。" type="info" :closable="false" />
              <el-input v-model="definitionText" type="textarea" :rows="18" class="definition" />
              <el-button type="primary" @click="saveVersion">创建新 Version</el-button>
            </el-tab-pane>
            <el-tab-pane label="Execution" name="execution">
              <el-alert title="可直接创建并运行当前已发布版本，也可以输入已有 Execution ID 查询、取消或 Retry。" type="info" :closable="false" />
              <el-input v-model="executionInputText" type="textarea" :rows="5" class="execution-input" placeholder='{"key":"value"}' />
              <div class="trace-query">
                <el-button type="primary" :loading="executionActionLoading" :disabled="!selected.published_version_id" @click="createExecution">创建 Execution</el-button>
                <el-button type="success" :loading="executionActionLoading" :disabled="!execution || execution.status !== 'pending'" @click="runExecution">运行 Execution</el-button>
                <el-button type="warning" :loading="executionActionLoading" :disabled="!execution || !['pending', 'running'].includes(execution.status)" @click="cancelExecution">取消 Execution</el-button>
                <el-button type="danger" :loading="executionActionLoading" :disabled="!execution || execution.status !== 'failed'" @click="retryExecution">Retry</el-button>
              </div>
              <div class="trace-query">
                <el-input v-model="executionId" placeholder="execution UUID" @keyup.enter="loadExecution" />
                <el-button type="primary" :loading="executionLoading" @click="loadExecution">查询执行</el-button>
              </div>
              <template v-if="execution">
                <el-descriptions :column="2" border class="execution-summary">
                  <el-descriptions-item label="Execution ID">{{ execution.id }}</el-descriptions-item>
                  <el-descriptions-item label="Status"><el-tag>{{ execution.status }}</el-tag></el-descriptions-item>
                  <el-descriptions-item label="Workflow Version">{{ execution.workflow_version_id }}</el-descriptions-item>
                  <el-descriptions-item label="Retry Of">{{ execution.retry_of_execution_id || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="Current Node">{{ execution.current_node_id || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="Started">{{ execution.started_at || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="Ended">{{ execution.ended_at || '-' }}</el-descriptions-item>
                  <el-descriptions-item v-if="execution.error_code" label="Error">{{ execution.error_code }}: {{ execution.error_message || '-' }}</el-descriptions-item>
                </el-descriptions>
                <el-table :data="executionNodes" class="execution-nodes">
                  <el-table-column prop="node_id" label="Node" min-width="140" />
                  <el-table-column prop="status" label="Status" width="110" />
                  <el-table-column prop="attempt" label="Attempt" width="90" />
                  <el-table-column prop="started_at" label="Started" min-width="170" />
                  <el-table-column prop="error_code" label="Error" width="140" />
                </el-table>
              </template>
              <el-empty v-else description="暂无 Execution" />
            </el-tab-pane>
            <el-tab-pane label="Audit" name="audit">
              <el-table v-loading="auditLoading" :data="audits">
                <el-table-column prop="action" label="Action" min-width="180" />
                <el-table-column prop="status" label="Status" width="110" />
                <el-table-column prop="created_at" label="Created" min-width="180" />
                <el-table-column prop="error_code" label="Error" width="130" />
              </el-table>
            </el-tab-pane>
            <el-tab-pane label="Trace" name="trace">
              <el-alert title="输入 Workflow Execution ID 查看完整 Trace。" type="info" :closable="false" />
              <div class="trace-query"><el-input v-model="traceExecutionId" placeholder="execution UUID" @keyup.enter="loadTrace" /><el-button type="primary" @click="loadTrace">查询 Trace</el-button></div>
              <el-timeline v-if="traces.length" class="trace-list">
                <el-timeline-item v-for="item in traces" :key="item.id" :timestamp="item.created_at">
                  <strong>{{ item.event_type }}</strong> / {{ item.status }} / node={{ item.node_id || '-' }}
                  <div v-if="item.error_code" class="error">{{ item.error_code }}: {{ item.error_message }}</div>
                </el-timeline-item>
              </el-timeline>
              <el-empty v-else description="暂无 Trace" />
            </el-tab-pane>
          </el-tabs>
        </el-card>
        <el-empty v-else description="请选择 Workflow" />
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.workflow-page { padding: 16px; }
.header { display: flex; align-items: center; justify-content: space-between; }
.definition { margin: 12px 0; font-family: monospace; }
.execution-input { margin-top: 12px; font-family: monospace; }
.trace-query { display: flex; gap: 8px; margin-top: 12px; }
.trace-query .el-input { flex: 1; }
.execution-summary { margin-top: 16px; }
.execution-nodes { margin-top: 16px; }
.trace-list { margin-top: 20px; }
.error { margin-top: 4px; }
</style>
