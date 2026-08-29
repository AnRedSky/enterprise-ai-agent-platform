<script setup lang="ts">
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import { createOrganization, listOrganizations, type Organization } from "@/api/organizations";

const organizations = ref<Organization[]>([]);
const loading = ref(false);
const error = ref("");
const dialogVisible = ref(false);
const saving = ref(false);
const name = ref("");

async function load() {
  loading.value = true;
  error.value = "";
  try {
    organizations.value = (await listOrganizations()).items;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "组织列表加载失败";
  } finally {
    loading.value = false;
  }
}

async function create() {
  if (!name.value.trim()) return;
  saving.value = true;
  try {
    await createOrganization({ name: name.value.trim() });
    name.value = "";
    dialogVisible.value = false;
    await load();
    ElMessage.success("组织创建成功");
  } catch (e) {
    ElMessage.error(e instanceof Error ? e.message : "组织创建失败");
  } finally {
    saving.value = false;
  }
}

function statusLabel(status: Organization["status"]) {
  return status === "active" ? "已启用" : "待处理";
}

onMounted(load);
</script>

<template>
  <div class="page">
    <div class="header">
      <div><h1>组织</h1><p>管理企业组织及成员访问权限。</p></div>
      <el-button type="primary" @click="dialogVisible = true">创建组织</el-button>
    </div>
    <el-alert v-if="error" :title="error" type="error" show-icon />
    <el-table v-loading="loading" :data="organizations" border class="table">
      <el-table-column prop="name" label="名称" min-width="220" />
      <el-table-column prop="tenant_id" label="Tenant ID" min-width="280" />
      <el-table-column label="状态" width="120"><template #default="{ row }"><el-tag :type="row.status === 'active' ? 'success' : 'warning'">{{ statusLabel(row.status) }}</el-tag></template></el-table-column>
      <el-table-column label="操作" width="130"><template #default="{ row }"><router-link :to="`/organizations/${row.id}`">管理成员</router-link></template></el-table-column>
    </el-table>
    <el-empty v-if="!loading && !organizations.length" description="暂无组织。" />
    <el-dialog v-model="dialogVisible" title="创建组织" width="480px">
      <el-form label-width="90px"><el-form-item label="名称" required><el-input v-model="name" maxlength="120" show-word-limit @keyup.enter="create" /></el-form-item></el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" :loading="saving" :disabled="!name.trim()" @click="create">创建</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>.page{padding:32px}.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:24px}.header p{color:#667085}.table{margin-top:18px}a{color:#409eff;text-decoration:none}</style>
