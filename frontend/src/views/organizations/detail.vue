<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { getUserId } from "@/api/auth";
import { addMember, getOrganization, listMembers, removeMember, transferOwner, updateMember, updateOrganization, type Membership, type Organization } from "@/api/organizations";
import PageHeader from "@/components/ui/PageHeader.vue";
import SurfaceCard from "@/components/ui/SurfaceCard.vue";
import StatePanel from "@/components/ui/StatePanel.vue";

const route = useRoute(); const router = useRouter(); const id = String(route.params.id);
const organization = ref<Organization | null>(null); const members = ref<Membership[]>([]); const loading = ref(true); const membersLoading = ref(false); const error = ref(""); const memberError = ref(""); const saving = ref(false);
const memberDialog = ref(false); const memberUserId = ref(""); const memberRole = ref<"admin" | "member">("member"); const editing = ref<Membership | null>(null); const editRole = ref<"admin" | "member">("member");
const currentPage = ref(1); const pageSize = 20; const totalMembers = ref(0);
const currentMembership = computed(() => members.value.find((member) => member.user_id === getUserId()));
const canManage = computed(() => currentMembership.value?.status === "active" && (currentMembership.value.role === "owner" || currentMembership.value.role === "admin"));
const canTransferOwner = computed(() => currentMembership.value?.status === "active" && currentMembership.value.role === "owner");
const pageState = computed(() => error.value ? "error" : loading.value ? "loading" : organization.value ? "success" : "empty");
function statusLabel(status: Organization["status"] | Membership["status"]) { return status === "active" ? "已启用（active）" : status === "suspended" ? "已暂停（suspended）" : `未知状态（${status}）`; }
function roleLabel(role: Membership["role"]) { return role === "owner" ? "所有者（owner）" : role === "admin" ? "管理员（admin）" : role === "member" ? "成员（member）" : `未知角色（${role}）`; }
function organizationLoadError(errorValue: unknown) { const status = (errorValue as { response?: { status?: number } } | null)?.response?.status; if (status === 403) return "组织详情加载失败：当前用户无权访问该组织。"; if (status === 404) return "组织详情加载失败：组织不存在或已不可访问。"; return "组织详情加载失败，请稍后重试"; }
function userError(value: unknown, fallback: string) { const status = (value as { response?: { status?: number } } | null)?.response?.status; return status === 403 ? "当前账号无权执行该操作。" : fallback; }
async function loadMembers(page = currentPage.value) { membersLoading.value = true; memberError.value = ""; try { const response = await listMembers(id, (page - 1) * pageSize, pageSize); members.value = response.items; totalMembers.value = response.total; currentPage.value = page; } catch (e) { memberError.value = userError(e, "成员列表加载失败，请刷新后重试"); } finally { membersLoading.value = false; } }
async function load() { loading.value = true; error.value = ""; try { organization.value = await getOrganization(id); await loadMembers(1); } catch (e) { organization.value = null; error.value = organizationLoadError(e); } finally { loading.value = false; } }
async function changePage(page: number) { if (page === currentPage.value || page < 1) return; await loadMembers(page); }
async function reloadMembers() { const page = currentPage.value; const maxPage = Math.max(1, Math.ceil(totalMembers.value / pageSize)); await loadMembers(Math.min(page, maxPage)); }
async function toggleOrganizationStatus() { if (!organization.value || !canManage.value || saving.value) return; const next = organization.value.status === "active" ? "suspended" : "active"; try { await ElMessageBox.confirm(`确定将组织设置为${next === "active" ? "已启用" : "已暂停"}吗？`, "状态变更确认", { type: "warning" }); saving.value = true; organization.value = await updateOrganization(id, { status: next }); ElMessage.success(`组织已${next === "active" ? "恢复" : "暂停"}`); } catch (e) { if (e !== "cancel" && e !== "close") ElMessage.error(userError(e, "组织状态更新失败，请稍后重试")); } finally { saving.value = false; } }
async function add() { if (!memberUserId.value.trim() || !canManage.value || saving.value) return; saving.value = true; try { await addMember(id, { user_id: memberUserId.value.trim(), role: memberRole.value }); memberDialog.value = false; memberUserId.value = ""; await loadMembers(1); ElMessage.success("成员添加成功"); } catch (e) { ElMessage.error(userError(e, "成员添加失败，请稍后重试")); } finally { saving.value = false; } }
function openEdit(member: Membership) { if (!canManage.value || member.role === "owner") return; editing.value = member; editRole.value = member.role === "admin" ? "admin" : "member"; }
async function saveEdit() { if (!editing.value || !canManage.value || saving.value) return; saving.value = true; try { await updateMember(id, editing.value.id, { role: editRole.value }); editing.value = null; await reloadMembers(); ElMessage.success("成员角色已更新"); } catch (e) { ElMessage.error(userError(e, "成员角色更新失败，请稍后重试")); } finally { saving.value = false; } }
async function toggleMember(member: Membership) { if (!canManage.value || member.role === "owner" || saving.value) return; const next = member.status === "active" ? "suspended" : "active"; try { await ElMessageBox.confirm(`确定将成员设置为${next === "active" ? "已启用" : "已暂停"}吗？`, "成员状态确认", { type: "warning" }); saving.value = true; await updateMember(id, member.id, { status: next }); await reloadMembers(); ElMessage.success(`成员已${next === "active" ? "恢复" : "暂停"}`); } catch (e) { if (e !== "cancel" && e !== "close") ElMessage.error(userError(e, "成员状态更新失败，请稍后重试")); } finally { saving.value = false; } }
async function remove(member: Membership) { if (!canManage.value || member.role === "owner" || saving.value) return; try { await ElMessageBox.confirm("移除后，该成员将失去组织访问权限。", "移除成员", { type: "warning" }); saving.value = true; await removeMember(id, member.id); await reloadMembers(); ElMessage.success("成员已移除"); } catch (e) { if (e !== "cancel" && e !== "close") ElMessage.error(userError(e, "成员移除失败，请稍后重试")); } finally { saving.value = false; } }
async function transfer(member: Membership) { if (!canTransferOwner.value || member.role === "owner" || saving.value) return; try { await ElMessageBox.confirm(`确认将组织所有权转移给 ${member.user_id}？当前所有者将降级为管理员。`, "转移所有权", { type: "warning", confirmButtonText: "确认转移" }); saving.value = true; await transferOwner(id, member.id); await reloadMembers(); ElMessage.success("所有权转移成功"); } catch (e) { if (e !== "cancel" && e !== "close") ElMessage.error(userError(e, "所有权转移失败，请稍后重试")); } finally { saving.value = false; } }
onMounted(load);
</script>
<template>
  <div class="page">
    <PageHeader :title="organization?.name || '组织详情'" description="管理组织状态、成员角色和访问权限。">
      <template #actions>
        <el-button @click="router.push('/organizations')">返回组织列表</el-button>
        <el-button v-if="organization && canManage" type="primary" @click="memberDialog = true">添加成员</el-button>
        <el-button v-if="organization && canManage" :loading="saving" :type="organization.status === 'active' ? 'warning' : 'success'" @click="toggleOrganizationStatus">{{ organization.status === "active" ? "暂停组织" : "恢复组织" }}</el-button>
        <el-button v-if="organization && canManage" type="primary" @click="router.push(`/organizations/${id}/model-providers`)">模型提供方 / 模型配置</el-button>
      </template>
    </PageHeader>

    <StatePanel v-if="pageState !== 'success'" :state="pageState" :title="pageState === 'loading' ? '正在加载组织详情' : pageState === 'error' ? '组织详情加载失败' : '组织不存在'" :description="pageState === 'loading' ? '正在同步组织和成员权限。' : error || '组织不存在或无权访问。'" :action-label="pageState === 'error' ? '重试' : undefined" @action="load" />

    <template v-else>
      <SurfaceCard title="组织信息" description="组织 ID 是当前详情上下文的 durable identifier。">
        <div class="identity"><strong>{{ organization.name }}</strong><span>{{ organization.id }}</span><el-tag :type="organization.status === 'active' ? 'success' : 'warning'">{{ statusLabel(organization.status) }}</el-tag></div>
      </SurfaceCard>
      <SurfaceCard class="members" title="成员" description="成员角色、状态和所有权操作均基于真实 membership ID。">
        <template #header><span class="member-count">共 {{ totalMembers }} 人</span></template>
        <StatePanel v-if="memberError" state="error" title="成员列表加载失败" :description="memberError" action-label="重试" @action="reloadMembers" />
        <template v-else-if="membersLoading">
          <StatePanel state="loading" title="正在加载成员" description="正在同步当前组织的成员和权限信息。" />
        </template>
        <template v-else>
          <el-table :data="members" border>
            <el-table-column prop="user_id" label="用户 ID（User ID）" min-width="280" />
            <el-table-column label="角色" width="170"><template #default="{ row }"><el-tag>{{ roleLabel(row.role) }}</el-tag></template></el-table-column>
            <el-table-column label="状态" width="170"><template #default="{ row }"><el-tag :type="row.status === 'active' ? 'success' : 'warning'">{{ statusLabel(row.status) }}</el-tag></template></el-table-column>
            <el-table-column v-if="canManage" label="操作" min-width="430"><template #default="{ row }"><div class="member-actions"><el-button v-if="row.role !== 'owner'" link type="primary" :disabled="saving" @click="openEdit(row as Membership)">编辑</el-button><el-button v-if="row.role !== 'owner'" link type="warning" :disabled="saving" @click="toggleMember(row as Membership)">{{ row.status === "active" ? "暂停" : "恢复" }}</el-button><el-button v-if="canTransferOwner && row.role !== 'owner'" link type="success" :disabled="saving" @click="transfer(row as Membership)">转移所有权</el-button><el-button v-if="row.role !== 'owner'" link type="danger" :disabled="saving" @click="remove(row as Membership)">移除</el-button></div></template></el-table-column>
          </el-table>
          <StatePanel v-if="!members.length" state="empty" title="暂无成员" description="当前组织还没有可管理的成员。" action-label="添加成员" @action="memberDialog = true" />
          <div v-if="totalMembers > pageSize" class="pagination-wrap"><el-pagination :current-page="currentPage" :page-size="pageSize" :total="totalMembers" layout="prev, pager, next" background @current-change="changePage" /></div>
        </template>
      </SurfaceCard>
    </template>

    <el-dialog v-model="memberDialog" title="添加成员" width="500px"><el-form label-width="90px"><el-form-item label="用户 ID（User ID）" required><el-input v-model="memberUserId" placeholder="输入用户 UUID" /></el-form-item><el-form-item label="角色"><el-select v-model="memberRole" style="width:100%"><el-option label="管理员（admin）" value="admin" /><el-option label="成员（member）" value="member" /></el-select></el-form-item></el-form><template #footer><el-button :disabled="saving" @click="memberDialog=false">取消</el-button><el-button type="primary" :loading="saving" :disabled="!memberUserId.trim()" @click="add">添加</el-button></template></el-dialog>
    <el-dialog :model-value="Boolean(editing)" title="编辑成员" width="420px" @close="editing=null"><el-form label-width="80px"><el-form-item label="角色"><el-select v-model="editRole" style="width:100%"><el-option label="管理员（admin）" value="admin" /><el-option label="成员（member）" value="member" /></el-select></el-form-item></el-form><template #footer><el-button :disabled="saving" @click="editing=null">取消</el-button><el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button></template></el-dialog>
  </div>
</template>
<style scoped>
.page{padding:var(--ui-space-8)}.identity{display:flex;align-items:center;gap:16px;flex-wrap:wrap;padding:18px 20px}.identity strong{font-size:16px;color:var(--ui-text-primary)}.identity span,.member-count{font-size:12px;color:var(--ui-text-tertiary)}.members{margin-top:var(--ui-space-5)}.member-actions{display:flex;align-items:center;flex-wrap:wrap;gap:2px}.pagination-wrap{display:flex;justify-content:flex-end;margin-top:18px}
@media(max-width:900px){.page{padding:var(--ui-space-5)}.pagination-wrap{justify-content:center}}@media(max-width:600px){.page{padding:var(--ui-space-3)}}
</style>
