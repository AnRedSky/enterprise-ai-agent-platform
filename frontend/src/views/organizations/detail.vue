<script setup lang="ts">
import { onMounted, ref, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { addMember, getOrganization, listMembers, removeMember, transferOwner, updateMember, updateOrganization, type Membership, type MembershipRole, type Organization } from "@/api/organizations";

const route = useRoute();
const router = useRouter();
const id = String(route.params.id);
const organization = ref<Organization | null>(null);
const members = ref<Membership[]>([]);
const loading = ref(false);
const error = ref("");
const saving = ref(false);
const memberDialog = ref(false);
const memberUserId = ref("");
const memberRole = ref<"admin" | "member">("member");
const editing = ref<Membership | null>(null);
const editRole = ref<"admin" | "member">("member");
const transferTarget = ref<Membership | null>(null);
const canManage = computed(() => true);

function asMembership(row: unknown): Membership {
  return row as Membership;
}

async function load() {
  loading.value = true; error.value = "";
  try {
    organization.value = await getOrganization(id);
    members.value = (await listMembers(id)).items;
  } catch (e) { error.value = e instanceof Error ? e.message : "Organization 详情加载失败"; }
  finally { loading.value = false; }
}

async function toggleOrganizationStatus() {
  if (!organization.value) return;
  const next = organization.value.status === "active" ? "suspended" : "active";
  try {
    await ElMessageBox.confirm(`确定将 Organization 设置为 ${next} 吗？`, "状态变更确认", { type: "warning" });
    saving.value = true;
    organization.value = await updateOrganization(id, { status: next });
    ElMessage.success(`Organization 已${next === "active" ? "恢复" : "暂停"}`);
  } catch (e) { if (e !== "cancel" && e !== "close") ElMessage.error(e instanceof Error ? e.message : "状态更新失败"); }
  finally { saving.value = false; }
}

async function add() {
  if (!memberUserId.value.trim()) return;
  saving.value = true;
  try { await addMember(id, { user_id: memberUserId.value.trim(), role: memberRole.value }); memberDialog.value = false; memberUserId.value = ""; members.value = (await listMembers(id)).items; ElMessage.success("成员添加成功"); }
  catch (e) { ElMessage.error(e instanceof Error ? e.message : "成员添加失败"); }
  finally { saving.value = false; }
}

function openEdit(member: Membership) { editing.value = member; editRole.value = member.role === "admin" ? "admin" : "member"; }
async function saveEdit() {
  if (!editing.value) return;
  saving.value = true;
  try { await updateMember(id, editing.value.id, { role: editRole.value }); editing.value = null; members.value = (await listMembers(id)).items; ElMessage.success("成员角色已更新"); }
  catch (e) { ElMessage.error(e instanceof Error ? e.message : "成员更新失败"); }
  finally { saving.value = false; }
}
async function toggleMember(member: Membership) {
  const next = member.status === "active" ? "suspended" : "active";
  try { await updateMember(id, member.id, { status: next }); members.value = (await listMembers(id)).items; ElMessage.success(`成员已${next === "active" ? "恢复" : "暂停"}`); }
  catch (e) { ElMessage.error(e instanceof Error ? e.message : "成员状态更新失败"); }
}
async function remove(member: Membership) {
  try { await ElMessageBox.confirm("移除后该成员将失去 Organization 访问权限。", "移除成员", { type: "warning" }); await removeMember(id, member.id); members.value = (await listMembers(id)).items; ElMessage.success("成员已移除"); }
  catch (e) { if (e !== "cancel" && e !== "close") ElMessage.error(e instanceof Error ? e.message : "成员移除失败"); }
}
async function transfer(member: Membership) {
  try { await ElMessageBox.confirm(`确认将 Organization 所有权转移给 ${member.user_id}？当前 Owner 将降级为 Admin。`, "转移所有权", { type: "warning", confirmButtonText: "确认转移" }); await transferOwner(id, member.id); members.value = (await listMembers(id)).items; ElMessage.success("所有权转移成功"); }
  catch (e) { if (e !== "cancel" && e !== "close") ElMessage.error(e instanceof Error ? e.message : "所有权转移失败"); }
}

onMounted(load);
</script>

<template>
  <div class="page">
    <div class="header"><el-button link @click="router.push('/organizations')">← Organizations</el-button><div v-if="organization" class="actions"><el-button :loading="saving" :type="organization.status === 'active' ? 'warning' : 'success'" @click="toggleOrganizationStatus">{{ organization.status === 'active' ? '暂停 Organization' : '恢复 Organization' }}</el-button><el-button type="primary" @click="memberDialog = true">添加成员</el-button></div></div>
    <el-alert v-if="error" :title="error" type="error" show-icon />
    <el-card v-if="organization" v-loading="loading"><template #header><div class="title"><div><h1>{{ organization.name }}</h1><span>{{ organization.id }}</span></div><el-tag :type="organization.status === 'active' ? 'success' : 'warning'">{{ organization.status }}</el-tag></div></template>
      <el-alert v-if="organization.status === 'suspended'" title="Organization 当前已暂停。管理操作仍由后端授权策略控制。" type="warning" show-icon class="notice" />
      <h2>成员</h2>
      <el-table :data="members" border>
        <el-table-column prop="user_id" label="User ID" min-width="280" />
        <el-table-column label="角色" width="130"><template #default="{ row }"><el-tag>{{ row.role }}</el-tag></template></el-table-column>
        <el-table-column label="状态" width="120"><template #default="{ row }"><el-tag :type="row.status === 'active' ? 'success' : 'warning'">{{ row.status }}</el-tag></template></el-table-column>
        <el-table-column v-if="canManage" label="操作" min-width="430"><template #default="{ row }"><el-button v-if="row.role !== 'owner'" link type="primary" @click="openEdit(asMembership(row))">编辑</el-button><el-button v-if="row.role !== 'owner'" link type="warning" @click="toggleMember(asMembership(row))">{{ row.status === 'active' ? '暂停' : '恢复' }}</el-button><el-button v-if="row.role !== 'owner'" link type="success" @click="transferTarget = asMembership(row); transfer(asMembership(row))">转移 Owner</el-button><el-button v-if="row.role !== 'owner'" link type="danger" @click="remove(asMembership(row))">移除</el-button></template></el-table-column>
      </el-table>
      <el-empty v-if="!members.length" description="暂无成员。" />
    </el-card>
    <el-empty v-else-if="!loading && !error" description="Organization 不存在或无权访问。" />

    <el-dialog v-model="memberDialog" title="添加成员" width="500px"><el-form label-width="90px"><el-form-item label="User ID" required><el-input v-model="memberUserId" placeholder="输入用户 UUID" /></el-form-item><el-form-item label="角色"><el-select v-model="memberRole" style="width:100%"><el-option label="Admin" value="admin" /><el-option label="Member" value="member" /></el-select></el-form-item></el-form><template #footer><el-button @click="memberDialog=false">取消</el-button><el-button type="primary" :loading="saving" :disabled="!memberUserId.trim()" @click="add">添加</el-button></template></el-dialog>
    <el-dialog :model-value="Boolean(editing)" title="编辑成员" width="420px" @close="editing=null"><el-form label-width="80px"><el-form-item label="角色"><el-select v-model="editRole" style="width:100%"><el-option label="Admin" value="admin" /><el-option label="Member" value="member" /></el-select></el-form-item></el-form><template #footer><el-button @click="editing=null">取消</el-button><el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button></template></el-dialog>
  </div>
</template>

<style scoped>.page{padding:32px}.header{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px}.actions{display:flex;gap:10px}.title{display:flex;justify-content:space-between;align-items:center}.title h1{margin:0 0 6px}.title span{color:#667085;font-size:12px}.notice{margin-bottom:20px}h2{margin:24px 0 14px}</style>
