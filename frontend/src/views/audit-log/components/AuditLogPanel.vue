<template>
  <el-card>
    <template #header>审计日志</template>
    <el-form inline @submit.prevent="load">
      <el-input v-model="status" placeholder="状态" clearable />
      <el-button type="primary" @click="load">查询</el-button>
    </el-form>
    <el-alert v-if="error" type="error" :closable="false" title="审计日志查询失败，请稍后重试" />
    <el-empty v-else-if="!loading && !items.length" description="暂无审计日志" />
    <el-table v-else :data="items" v-loading="loading">
      <el-table-column prop="id" label="ID" min-width="260" />
      <el-table-column label="操作"><template #default="{ row }"><span>{{ actionLabel(row.action) }}</span></template></el-table-column>
      <el-table-column label="状态"><template #default="{ row }"><span>{{ statusLabel(row.status) }}</span></template></el-table-column>
      <el-table-column prop="agent_id" label="智能体" min-width="220" />
      <el-table-column prop="tool_id" label="工具" min-width="220" />
      <el-table-column prop="created_at" label="创建时间" />
    </el-table>
    <el-pagination v-if="total" v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" @change="load" />
  </el-card>
</template>
<script setup lang="ts">
import { onMounted, ref } from "vue";
import { runtimeApi, type AuditLog } from "../../../api/runtime";
const items = ref<AuditLog[]>([]);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const status = ref("");
const loading = ref(false);
const error = ref(false);
const actionLabels: Record<string, string> = { create: "创建", update: "更新", delete: "删除", publish: "发布", archive: "归档", execute: "执行", cancel: "取消", retry: "重试", resume: "恢复", bind: "绑定", unbind: "解绑", enable: "启用", disable: "停用" };
const resourceLabels: Record<string, string> = { agent: "智能体", tool: "工具", workflow: "工作流", knowledge: "知识库", model: "模型", organization: "组织", integration: "集成" };
function actionLabel(value: unknown) {
  if (typeof value !== "string" || !value) return "未知操作";
  const direct = actionLabels[value];
  if (direct) return `${direct}（${value}）`;
  const [resource, action] = value.split(".", 2);
  if (action && actionLabels[action]) return `${resourceLabels[resource] || "资源"}${actionLabels[action]}（${value}）`;
  return `未知操作（${value}）`;
}
function statusLabel(value: unknown) {
  const labels: Record<string, string> = { success: "成功", succeeded: "成功", failed: "失败", running: "运行中", pending: "等待中", cancelled: "已取消", completed: "已完成" };
  if (typeof value !== "string") return "未知状态";
  return `${labels[value.toLowerCase()] ?? "未知状态"}（${value}）`;
}
async function load() {
  loading.value = true;
  error.value = false;
  try {
    const response = await runtimeApi.auditLogs({ page: page.value, page_size: pageSize.value, ...(status.value ? { status: status.value } : {}) });
    items.value = response.data.items ?? [];
    total.value = response.data.total ?? 0;
  } catch (err) {
    console.error("审计日志查询失败", err);
    items.value = [];
    total.value = 0;
    error.value = true;
  } finally {
    loading.value = false;
  }
}
onMounted(() => void load());
</script>
