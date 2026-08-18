<template>
  <el-card>
    <template #header>Audit Logs</template>

    <el-form inline @submit.prevent="load">
      <el-input v-model="status" placeholder="Status" clearable />
      <el-button type="primary" @click="load">查询</el-button>
    </el-form>

    <el-alert
      v-if="error"
      type="error"
      :closable="false"
      title="Audit 查询失败"
    />

    <el-empty
      v-else-if="!loading && !items.length"
      description="暂无 Audit Log"
    />

    <el-table v-else :data="items" v-loading="loading">
      <el-table-column prop="id" label="ID" min-width="260" />
      <el-table-column prop="action" label="Action" />
      <el-table-column prop="status" label="Status" />
      <el-table-column prop="agent_id" label="Agent" min-width="220" />
      <el-table-column prop="tool_id" label="Tool" min-width="220" />
      <el-table-column prop="created_at" label="Created At" />
    </el-table>

    <el-pagination
      v-if="total"
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      :page-sizes="[10, 20, 50, 100]"
      layout="total, sizes, prev, pager, next"
      @change="load"
    />
  </el-card>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { runtimeApi, type AuditLog } from "../api/runtime";

const items = ref<AuditLog[]>([]);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const status = ref("");
const loading = ref(false);
const error = ref(false);

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
  } catch (err) {
    // 查询异常必须在组件内部消费，避免 rejected Promise 冒泡为未处理异常。
    console.error("AuditLog query failed", err);
    items.value = [];
    total.value = 0;
    error.value = true;
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void load();
});
</script>
