<template>
  <el-card>
    <template #header>Audit Logs</template>
    <el-form inline @submit.prevent="load"><el-input v-model="status" placeholder="Status" clearable /><el-button type="primary" @click="load">查询</el-button></el-form>
    <el-alert v-if="error" type="error" :closable="false" title="Audit 查询失败" />
    <el-empty v-else-if="!loading && !items.length" description="暂无 Audit Log" />
    <el-table v-else :data="items" v-loading="loading"><el-table-column prop="id" label="ID" min-width="260" /><el-table-column prop="action" label="Action" /><el-table-column prop="status" label="Status" /><el-table-column prop="agent_id" label="Agent" min-width="220" /><el-table-column prop="tool_id" label="Tool" min-width="220" /><el-table-column prop="created_at" label="Created At" /></el-table>
    <el-pagination v-if="total" v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10,20,50,100]" layout="total, sizes, prev, pager, next" @change="load" />
  </el-card>
</template>
<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { runtimeApi, type AuditLog } from "../api/runtime";
const items = ref<AuditLog[]>([]), page = ref(1), pageSize = ref(20), total = ref(0), status = ref(""), loading = ref(false), error = ref(false);
async function load() { loading.value = true; error.value = false; try { const r = await runtimeApi.auditLogs({ page: page.value, page_size: pageSize.value, ...(status.value ? { status: status.value } : {}) }); items.value = r.data.items; total.value = r.data.total; } catch { error.value = true; ElMessage.error("Audit 查询失败"); } finally { loading.value = false; } }
onMounted(load);
</script>
