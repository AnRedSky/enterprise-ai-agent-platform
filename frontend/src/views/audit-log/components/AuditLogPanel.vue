<template>
  <section class="audit-panel" aria-label="审计日志">
    <el-card shadow="never">
      <template #header>
        <div class="panel-header">
          <div>
            <span class="eyebrow">运行治理</span>
            <h1>审计日志</h1>
            <p>按状态筛选真实运行操作记录；Execution 关联可直接进入运行诊断。</p>
          </div>
          <el-button :loading="loading" @click="load">刷新</el-button>
        </div>
      </template>

      <el-form inline @submit.prevent="load" class="filter-form">
        <el-form-item label="状态">
          <el-select v-model="status" clearable placeholder="全部状态" class="status-select">
            <el-option v-for="option in statusOptions" :key="option.value" :label="option.label" :value="option.value" />
          </el-select>
        </el-form-item>
        <el-button type="primary" @click="load">查询</el-button>
        <el-button v-if="status" @click="resetFilters">重置</el-button>
      </el-form>

      <el-alert
        v-if="error"
        title="审计日志暂时无法加载，请检查服务连接后重试"
        type="error"
        :closable="false"
        show-icon
      >
        <template #default>
          <el-button type="danger" link @click="load">重新加载</el-button>
        </template>
      </el-alert>

      <el-empty v-else-if="!loading && !items.length" description="暂无符合条件的审计日志">
        <el-button type="primary" plain @click="resetFilters">查看全部记录</el-button>
      </el-empty>

      <div v-else class="table-wrap">
        <el-table v-loading="loading" :data="items" stripe row-key="id" aria-label="审计日志列表">
          <el-table-column prop="id" label="记录 ID" min-width="240" show-overflow-tooltip />
          <el-table-column label="操作" min-width="160">
            <template #default="{ row }">{{ actionLabel(row.action) }}</template>
          </el-table-column>
          <el-table-column label="状态" min-width="130">
            <template #default="{ row }">
              <el-tag :type="statusType(row.status)" effect="plain">{{ statusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="agent_id" label="智能体" min-width="180" show-overflow-tooltip />
          <el-table-column prop="tool_id" label="工具" min-width="180" show-overflow-tooltip />
          <el-table-column label="Execution" min-width="180">
            <template #default="{ row }">
              <el-button v-if="row.execution_id" link type="primary" @click="openExecution(row.execution_id)">
                {{ compactId(row.execution_id) }}
              </el-button>
              <span v-else class="muted">—</span>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" min-width="180" />
        </el-table>
      </div>

      <div v-if="total" class="pagination-wrap">
        <span class="result-summary">共 {{ total }} 条记录</span>
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="sizes, prev, pager, next"
          @change="load"
        />
      </div>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { runtimeApi, type AuditLog } from "../../../api/runtime";

const router = useRouter();
const items = ref<AuditLog[]>([]);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const status = ref("");
const loading = ref(false);
const error = ref(false);

const statusOptions = [
  { value: "success", label: "成功" },
  { value: "failed", label: "失败" },
  { value: "running", label: "运行中" },
  { value: "pending", label: "等待中" },
  { value: "cancelled", label: "已取消" },
  { value: "completed", label: "已完成" },
];

const actionLabels: Record<string, string> = {
  create: "创建", update: "更新", delete: "删除", publish: "发布", archive: "归档",
  execute: "执行", cancel: "取消", retry: "重试", resume: "恢复", bind: "绑定",
  unbind: "解绑", enable: "启用", disable: "停用",
};
const resourceLabels: Record<string, string> = {
  agent: "智能体", tool: "工具", workflow: "工作流", knowledge: "知识库",
  model: "模型", organization: "组织", integration: "集成",
};

function actionLabel(value: unknown) {
  if (typeof value !== "string" || !value) return "未知操作";
  const direct = actionLabels[value];
  if (direct) return `${direct}（${value}）`;
  const [resource, action] = value.split(".", 2);
  if (action && actionLabels[action]) return `${resourceLabels[resource] || "资源"}${actionLabels[action]}（${value}）`;
  return `未知操作（${value}）`;
}

function statusLabel(value: unknown) {
  const labels: Record<string, string> = {
    success: "成功", succeeded: "成功", failed: "失败", running: "运行中",
    pending: "等待中", cancelled: "已取消", completed: "已完成",
  };
  if (typeof value !== "string") return "未知状态";
  return `${labels[value.toLowerCase()] ?? "未知状态"}（${value}）`;
}

function statusType(value: unknown): "success" | "danger" | "warning" | "info" {
  if (typeof value !== "string") return "info";
  const normalized = value.toLowerCase();
  if (["success", "succeeded", "completed"].includes(normalized)) return "success";
  if (["failed", "cancelled"].includes(normalized)) return "danger";
  if (["running", "pending"].includes(normalized)) return "warning";
  return "info";
}

function compactId(value: string) {
  return value.length > 18 ? `${value.slice(0, 8)}…${value.slice(-6)}` : value;
}

function resetFilters() {
  status.value = "";
  page.value = 1;
  void load();
}

function openExecution(executionId: string) {
  void router.push({ path: "/runtime", query: { execution_id: executionId, source: "audit" } });
}

async function load() {
  loading.value = true;
  error.value = false;
  try {
    const response = await runtimeApi.auditLogs({
      page: page.value,
      page_size: pageSize.value,
      ...(status.value ? { status: status.value } : {}),
    });
    items.value = response.data.items ?? [];
    total.value = response.data.total ?? 0;
  } catch {
    items.value = [];
    total.value = 0;
    error.value = true;
  } finally {
    loading.value = false;
  }
}

onMounted(() => void load());
</script>

<style scoped>
.audit-panel{padding:20px 32px}.audit-panel :deep(.el-card){border:1px solid #e4e7ed;border-radius:12px}.panel-header{display:flex;align-items:flex-start;justify-content:space-between;gap:20px}.eyebrow{font-size:10px;font-weight:700;letter-spacing:.08em;color:#667085}.panel-header h1{margin:4px 0;font-size:20px;color:#101828}.panel-header p{margin:0;color:#667085;font-size:12px}.filter-form{margin:18px 0}.filter-form :deep(.el-form-item){margin-bottom:0}.status-select{width:180px}.table-wrap{overflow-x:auto}.pagination-wrap{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-top:16px}.result-summary{font-size:12px;color:#667085}.muted{color:#98a2b3}@media(max-width:900px){.audit-panel{padding:14px}.panel-header{flex-direction:column}.filter-form{display:flex;flex-wrap:wrap}.pagination-wrap{align-items:flex-start;flex-direction:column}}@media(max-width:600px){.status-select{width:100%}.filter-form :deep(.el-form-item){width:100%}.filter-form :deep(.el-button){margin-left:0}.pagination-wrap :deep(.el-pagination){max-width:100%;overflow-x:auto}}
</style>
