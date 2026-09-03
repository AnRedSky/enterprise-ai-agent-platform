<template>
  <section class="audit-panel" aria-label="审计日志">
    <PageToolbar title="审计记录" description="按状态筛选真实运行操作记录；Execution 关联使用后端返回的 durable ID。">
      <el-button type="primary" :loading="loading" @click="load">查询</el-button>
      <el-button :loading="loading" @click="resetFilters">重置</el-button>
    </PageToolbar>
    <SurfaceCard title="筛选条件" description="仅提交显式筛选条件，不根据记录顺序推断关联关系。">
      <div class="filter-form">
        <el-select v-model="status" clearable placeholder="全部状态" class="status-select" @change="page = 1">
          <el-option v-for="option in statusOptions" :key="option.value" :label="option.label" :value="option.value" />
        </el-select>
        <el-button :loading="loading" @click="load">应用筛选</el-button>
      </div>
    </SurfaceCard>
    <div v-if="successMessage" class="success-message" role="status">{{ successMessage }}</div>

    <StatePanel v-if="loading && !items.length" state="loading" title="正在加载审计日志" description="正在同步审计记录，请稍候。" />
    <StatePanel v-else-if="permissionDenied" state="permission" title="无权查看审计日志" description="当前账号没有审计日志查询权限，请联系管理员。" />
    <StatePanel v-else-if="error" state="error" title="审计日志加载失败" description="暂时无法获取审计记录；当前结果已清空，请重试。" action-label="重新加载" @action="load" />
    <StatePanel v-else-if="!items.length" state="empty" title="暂无符合条件的审计日志" description="当前筛选条件没有匹配记录。" action-label="查看全部记录" @action="resetFilters" />
    <SurfaceCard v-else title="审计记录" :description="`当前页 ${items.length} 条，共 ${total} 条`">
      <div class="table-wrap">
        <el-table :data="items" stripe row-key="id" aria-label="审计日志列表">
          <el-table-column prop="id" label="记录 ID" min-width="240" show-overflow-tooltip />
          <el-table-column label="操作" min-width="160"><template #default="{ row }">{{ actionLabel(row.action) }}</template></el-table-column>
          <el-table-column label="状态" min-width="130"><template #default="{ row }"><el-tag :type="statusType(row.status)" effect="plain">{{ statusLabel(row.status) }}</el-tag></template></el-table-column>
          <el-table-column prop="agent_id" label="智能体" min-width="180" show-overflow-tooltip />
          <el-table-column prop="tool_id" label="工具" min-width="180" show-overflow-tooltip />
          <el-table-column label="Execution" min-width="180"><template #default="{ row }"><el-button v-if="row.execution_id" link type="primary" @click="openExecution(row.execution_id)">{{ compactId(row.execution_id) }}</el-button><span v-else class="muted">—</span></template></el-table-column>
          <el-table-column prop="created_at" label="创建时间" min-width="180" />
        </el-table>
      </div>
      <div v-if="total" class="pagination-wrap">
        <span class="result-summary">共 {{ total }} 条记录</span>
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10,20,50,100]" layout="sizes, prev, pager, next" @change="load" />
      </div>
    </SurfaceCard>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { runtimeApi, type AuditLog } from "../../../api/runtime";
import PageToolbar from "@/components/ui/PageToolbar.vue";
import StatePanel from "@/components/ui/StatePanel.vue";
import SurfaceCard from "@/components/ui/SurfaceCard.vue";

const router = useRouter();
const items = ref<AuditLog[]>([]);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const status = ref("");
const loading = ref(true);
const error = ref(false);
const permissionDenied = ref(false);
const successMessage = ref("");
const statusOptions = [
  { value: "success", label: "成功" }, { value: "failed", label: "失败" }, { value: "running", label: "运行中" },
  { value: "pending", label: "等待中" }, { value: "cancelled", label: "已取消" }, { value: "completed", label: "已完成" },
];
const actionLabels: Record<string, string> = { create: "创建", update: "更新", delete: "删除", publish: "发布", archive: "归档", execute: "执行", cancel: "取消", retry: "重试", resume: "恢复", bind: "绑定", unbind: "解绑", enable: "启用", disable: "停用" };
const resourceLabels: Record<string, string> = { agent: "智能体", tool: "工具", workflow: "工作流", knowledge: "知识库", model: "模型", organization: "组织", integration: "集成" };
function actionLabel(value: unknown) { if (typeof value !== "string" || !value) return "未知操作"; if (actionLabels[value]) return `${actionLabels[value]}（${value}）`; const [resource, action] = value.split(".", 2); return action && actionLabels[action] ? `${resourceLabels[resource] || "资源"}${actionLabels[action]}（${value}）` : `未知操作（${value}）`; }
function statusLabel(value: unknown) { const labels: Record<string, string> = { success: "成功", succeeded: "成功", failed: "失败", running: "运行中", pending: "等待中", cancelled: "已取消", completed: "已完成" }; if (typeof value !== "string") return "未知状态"; return `${labels[value.toLowerCase()] ?? "未知状态"}（${value}）`; }
function statusType(value: unknown): "success" | "danger" | "warning" | "info" { if (typeof value !== "string") return "info"; const v = value.toLowerCase(); if (["success", "succeeded", "completed"].includes(v)) return "success"; if (["failed", "cancelled"].includes(v)) return "danger"; if (["running", "pending"].includes(v)) return "warning"; return "info"; }
function compactId(value: string) { return value.length > 18 ? `${value.slice(0, 8)}…${value.slice(-6)}` : value; }
function resetFilters() { status.value = ""; page.value = 1; void load(); }
function openExecution(executionId: string) { void router.push({ path: "/runtime", query: { execution_id: executionId, source: "audit" } }); }
async function load() {
  loading.value = true;
  error.value = false;
  permissionDenied.value = false;
  successMessage.value = "";
  try {
    const response = await runtimeApi.auditLogs({ page: page.value, page_size: pageSize.value, ...(status.value ? { status: status.value } : {}) });
    items.value = response.data.items ?? [];
    total.value = response.data.total ?? 0;
    successMessage.value = "审计日志已更新";
  } catch (e: any) {
    items.value = [];
    total.value = 0;
    permissionDenied.value = e?.response?.status === 403;
    error.value = !permissionDenied.value;
  } finally { loading.value = false; }
}
onMounted(() => void load());
</script>

<style scoped>
.audit-panel { display:grid; gap:var(--ui-space-4); }
.filter-form { display:flex; gap:10px; align-items:center; padding:16px 20px; }
.status-select { width:180px; }
.success-message { padding:10px 14px; border:1px solid var(--ui-border-default); border-radius:var(--ui-radius-md); color:var(--ui-text-secondary); background:var(--ui-bg-subtle); font-size:12px; }
.table-wrap { overflow-x:auto; }
.pagination-wrap { display:flex; align-items:center; justify-content:space-between; gap:16px; margin-top:16px; }
.result-summary,.muted { font-size:12px; color:var(--ui-text-tertiary); }
@media(max-width:600px){.status-select{width:100%}.filter-form{align-items:stretch;flex-direction:column}.pagination-wrap{align-items:flex-start;flex-direction:column}}
</style>
