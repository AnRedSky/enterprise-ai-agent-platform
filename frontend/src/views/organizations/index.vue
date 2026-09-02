<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import PageHeader from "@/components/ui/PageHeader.vue";
import SurfaceCard from "@/components/ui/SurfaceCard.vue";
import StatePanel from "@/components/ui/StatePanel.vue";
import { createOrganization, listOrganizations, type Organization } from "@/api/organizations";

const organizations = ref<Organization[]>([]);
const loading = ref(true);
const error = ref("");
const permissionDenied = ref(false);
const dialogVisible = ref(false);
const saving = ref(false);
const name = ref("");

function userError(value: unknown, fallback: string) {
  const status = (value as { response?: { status?: number } } | null)?.response?.status;
  return status === 403 ? "当前账号没有组织访问权限，请联系管理员。" : fallback;
}

const pageState = computed(() => {
  if (permissionDenied.value) return "permission" as const;
  if (error.value) return "error" as const;
  if (loading.value) return "loading" as const;
  if (!organizations.value.length) return "empty" as const;
  return "success" as const;
});

async function load() {
  loading.value = true;
  error.value = "";
  permissionDenied.value = false;
  try {
    organizations.value = (await listOrganizations()).items;
  } catch (e) {
    permissionDenied.value = (e as { response?: { status?: number } } | null)?.response?.status === 403;
    error.value = userError(e, "组织列表加载失败，请稍后重试");
  } finally {
    loading.value = false;
  }
}

async function create() {
  const organizationName = name.value.trim();
  if (!organizationName || saving.value) return;
  saving.value = true;
  try {
    await createOrganization({ name: organizationName });
    name.value = "";
    dialogVisible.value = false;
    await load();
    ElMessage.success("组织创建成功");
  } catch (e) {
    ElMessage.error(userError(e, "组织创建失败，请稍后重试"));
  } finally {
    saving.value = false;
  }
}

function handleStateAction() {
  if (pageState.value === "empty") dialogVisible.value = true;
  if (pageState.value === "error") void load();
}

function statusLabel(status: Organization["status"]) {
  return status === "active" ? "已启用（active）" : status === "suspended" ? "已暂停（suspended）" : `未知状态（${status}）`;
}

onMounted(load);
</script>

<template>
  <div class="page">
    <PageHeader title="组织" description="管理企业组织及成员访问权限。">
      <template #actions>
        <el-button type="primary" @click="dialogVisible = true">创建组织</el-button>
      </template>
    </PageHeader>

    <StatePanel
      v-if="pageState !== 'success'"
      :state="pageState"
      :title="pageState === 'loading' ? '正在加载组织' : pageState === 'empty' ? '暂无组织' : pageState === 'permission' ? '无权访问组织' : '组织列表加载失败'"
      :description="pageState === 'loading' ? '正在同步组织及访问权限。' : pageState === 'empty' ? '创建第一个组织后即可管理成员。' : pageState === 'permission' ? '当前账号没有组织访问权限，请联系管理员。' : error"
      :action-label="pageState === 'error' ? '重试' : pageState === 'empty' ? '创建组织' : undefined"
      @action="handleStateAction"
    />

    <SurfaceCard v-else title="组织列表" description="组织详情通过真实 organization_id 深链进入成员管理。">
      <el-table :data="organizations" border class="table">
        <el-table-column prop="name" label="名称" min-width="220" />
        <el-table-column prop="tenant_id" label="租户 ID" min-width="280" />
        <el-table-column label="状态" width="170">
          <template #default="{ row }"><el-tag :type="row.status === 'active' ? 'success' : 'warning'">{{ statusLabel(row.status) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" width="130">
          <template #default="{ row }"><router-link :to="`/organizations/${row.id}`">管理成员</router-link></template>
        </el-table-column>
      </el-table>
    </SurfaceCard>

    <el-dialog v-model="dialogVisible" title="创建组织" width="480px">
      <el-form label-width="90px">
        <el-form-item label="名称" required>
          <el-input v-model="name" maxlength="120" show-word-limit @keyup.enter="create" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button :disabled="saving" @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" :disabled="!name.trim()" @click="create">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page { padding: var(--ui-space-8); }
.table { width: 100%; }
a { color: var(--ui-color-primary-600); text-decoration: none; }
@media (max-width: 700px) { .page { padding: var(--ui-space-5); } }
</style>
