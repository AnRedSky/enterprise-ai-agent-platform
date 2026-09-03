<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import ConfirmDialog from "@/components/ui/ConfirmDialog.vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import StatePanel from "@/components/ui/StatePanel.vue";
import SurfaceCard from "@/components/ui/SurfaceCard.vue";
import { createModelProfile, createModelProvider, deleteModelProfile, deleteModelProvider, listModelProfiles, listModelProviders, updateModelProfile, updateModelProvider, type ModelProfile, type ModelProfileCreatePayload, type ModelProvider, type ModelProviderCreatePayload, type ModelProviderUpdatePayload } from "@/api/modelProviders";

const route = useRoute();
const router = useRouter();
const organizationId = String(route.params.id);
const providers = ref<ModelProvider[]>([]);
const profiles = ref<Record<string, ModelProfile[]>>({});
const profileLoading = ref<Record<string, boolean>>({});
const profileErrors = ref<Record<string, string>>({});
const loading = ref(false);
const error = ref("");
const providerSaving = ref(false);
const profileSaving = ref(false);
const deletingProviderId = ref("");
const deletingProfileId = ref("");
const providerDialog = ref(false);
const profileDialog = ref(false);
const editingProvider = ref<ModelProvider | null>(null);
const editingProfile = ref<ModelProfile | null>(null);
const selectedProviderId = ref("");
const confirmTarget = ref<{ kind: "provider" | "profile"; provider?: ModelProvider; profile?: ModelProfile } | null>(null);
const providerForm = ref<ModelProviderCreatePayload>({ organization_id: organizationId, name: "", provider_type: "ollama", provider_name: "", endpoint: "", credential_ref: "", enabled: true, metadata: {} });
const profileForm = ref<ModelProfileCreatePayload>({ name: "", model_type: "chat", model_name: "", dimension: null, capabilities: {}, parameters: {}, enabled: true, is_default: false });
const providerTypeLabels: Record<string, string> = { ollama: "本地模型服务", openai: "OpenAI 兼容服务", azure_openai: "Azure OpenAI", anthropic: "Anthropic", custom: "自定义模型服务" };
const modelTypeLabels: Record<string, string> = { chat: "对话模型", embedding: "向量模型", rerank: "重排模型" };
const pageState = computed(() => loading.value ? "loading" : error.value ? "error" : providers.value.length ? "success" : "empty");
function displayType(value: unknown, labels: Record<string, string>, fallback: string) { if (typeof value !== "string" || !value) return fallback; return labels[value] ? `${labels[value]}（${value}）` : `未知类型（${value}）`; }
function providerTypeLabel(value: unknown) { return displayType(value, providerTypeLabels, "未知提供方类型"); }
function modelTypeLabel(value: unknown) { return displayType(value, modelTypeLabels, "未知模型类型"); }
function userError(value: unknown, fallback: string) { if (value instanceof Error && value.message.trim() && !/^\s*(4\d\d|5\d\d)\b/.test(value.message)) return value.message.trim(); return fallback; }
function isPermissionError(value: unknown) { return value instanceof Error && /^\s*403\b/.test(value.message); }
function resetProvider() { editingProvider.value = null; providerForm.value = { organization_id: organizationId, name: "", provider_type: "ollama", provider_name: "", endpoint: "", credential_ref: "", enabled: true, metadata: {} }; }
function resetProfile(providerId: string) { editingProfile.value = null; selectedProviderId.value = providerId; profileForm.value = { name: "", model_type: "chat", model_name: "", dimension: null, capabilities: {}, parameters: {}, enabled: true, is_default: false }; }
async function loadProfiles(providerId: string) { profileLoading.value = { ...profileLoading.value, [providerId]: true }; profileErrors.value = { ...profileErrors.value, [providerId]: "" }; try { profiles.value = { ...profiles.value, [providerId]: await listModelProfiles(providerId) }; } catch (e) { profiles.value = { ...profiles.value, [providerId]: [] }; profileErrors.value = { ...profileErrors.value, [providerId]: userError(e, "模型配置加载失败，请稍后重试") }; } finally { profileLoading.value = { ...profileLoading.value, [providerId]: false }; } }
async function load() { loading.value = true; error.value = ""; profiles.value = {}; try { const response = await listModelProviders(organizationId); providers.value = response.items; await Promise.all(providers.value.map((provider) => loadProfiles(provider.id))); } catch (e) { providers.value = []; error.value = userError(e, "模型提供方加载失败，请稍后重试"); } finally { loading.value = false; } }
function openCreateProvider() { resetProvider(); providerDialog.value = true; }
function openEditProvider(provider: ModelProvider) { editingProvider.value = provider; providerForm.value = { organization_id: organizationId, name: provider.name, provider_type: provider.provider_type, provider_name: provider.provider_name, endpoint: provider.endpoint ?? "", credential_ref: provider.credential_ref ?? "", enabled: provider.enabled, metadata: provider.metadata }; providerDialog.value = true; }
async function saveProvider() { if (providerSaving.value || !providerForm.value.name.trim() || !providerForm.value.provider_name.trim()) return; providerSaving.value = true; try { if (editingProvider.value) await updateModelProvider(editingProvider.value.id, { name: providerForm.value.name, endpoint: providerForm.value.endpoint, credential_ref: providerForm.value.credential_ref, enabled: providerForm.value.enabled, metadata: providerForm.value.metadata }); else await createModelProvider(providerForm.value); providerDialog.value = false; await load(); ElMessage.success("模型提供方保存成功"); } catch (e) { ElMessage.error(userError(e, "模型提供方保存失败，请稍后重试")); } finally { providerSaving.value = false; } }
function requestDeleteProvider(provider: ModelProvider) { if (!deletingProviderId.value) confirmTarget.value = { kind: "provider", provider }; }
function requestDeleteProfile(profile: ModelProfile) { if (!deletingProfileId.value) confirmTarget.value = { kind: "profile", profile }; }
async function confirmDelete() { const target = confirmTarget.value; if (!target) return; if (target.kind === "provider" && target.provider) { deletingProviderId.value = target.provider.id; try { await deleteModelProvider(target.provider.id); confirmTarget.value = null; await load(); ElMessage.success("模型提供方已删除"); } catch (e) { ElMessage.error(userError(e, "模型提供方删除失败，请稍后重试")); } finally { deletingProviderId.value = ""; } return; } if (target.profile) { deletingProfileId.value = target.profile.id; try { await deleteModelProfile(target.profile.id); confirmTarget.value = null; await loadProfiles(target.profile.provider_id); ElMessage.success("模型配置已删除"); } catch (e) { ElMessage.error(userError(e, "模型配置删除失败，请稍后重试")); } finally { deletingProfileId.value = ""; } } }
function cancelDelete() { if (!deletingProviderId.value && !deletingProfileId.value) confirmTarget.value = null; }
function openCreateProfile(providerId: string) { resetProfile(providerId); profileDialog.value = true; }
function openEditProfile(profile: ModelProfile) { editingProfile.value = profile; selectedProviderId.value = profile.provider_id; profileForm.value = { name: profile.name, model_type: profile.model_type, model_name: profile.model_name, dimension: profile.dimension, capabilities: profile.capabilities, parameters: profile.parameters, enabled: profile.enabled, is_default: profile.is_default }; profileDialog.value = true; }
async function saveProfile() { if (profileSaving.value || !profileForm.value.name.trim() || !profileForm.value.model_name.trim() || !selectedProviderId.value) return; const providerId = selectedProviderId.value; const payload = { ...profileForm.value, dimension: profileForm.value.model_type === "embedding" ? profileForm.value.dimension : null }; profileSaving.value = true; try { if (editingProfile.value) await updateModelProfile(editingProfile.value.id, payload); else await createModelProfile(providerId, payload); profileDialog.value = false; await loadProfiles(providerId); ElMessage.success("模型配置保存成功"); } catch (e) { ElMessage.error(userError(e, "模型配置保存失败，请稍后重试")); } finally { profileSaving.value = false; } }
function profileState(providerId: string) { if (profileLoading.value[providerId]) return "loading"; if (profileErrors.value[providerId]) return isPermissionError(profileErrors.value[providerId]) ? "permission" : "error"; if (!(profiles.value[providerId] ?? []).length) return "empty"; return "success"; }
function profileStateDescription(providerId: string) { if (profileErrors.value[providerId]) return profileErrors.value[providerId]; if (profileState(providerId) === "empty") return "当前提供方还没有模型配置，可直接创建一个。"; return ""; }
onMounted(load);
</script>

<template>
  <div class="page">
    <PageHeader eyebrow="Organization / Model Providers" title="模型提供方与模型配置" description="管理组织范围内的模型提供方和模型配置。凭据仅保存引用，不在页面展示密钥。">
      <template #actions><el-button @click="router.push(`/organizations/${organizationId}`)">返回组织</el-button><el-button :loading="loading" @click="load">刷新</el-button><el-button type="primary" @click="openCreateProvider">创建模型提供方</el-button></template>
    </PageHeader>

    <StatePanel v-if="pageState === 'loading'" state="loading" title="正在加载模型提供方" description="正在读取组织范围内的提供方及其模型配置。" />
    <StatePanel v-else-if="pageState === 'error'" :state="isPermissionError(error) ? 'permission' : 'error'" :title="isPermissionError(error) ? '无权查看模型提供方' : '模型提供方加载失败'" :description="isPermissionError(error) ? '当前账号没有访问该组织模型配置的权限。' : error" action-label="重新加载" @action="load" />
    <StatePanel v-else-if="pageState === 'empty'" state="empty" title="暂无模型提供方" description="当前组织还没有模型提供方。创建提供方后即可继续添加模型配置。" action-label="创建模型提供方" @action="openCreateProvider" />

    <template v-else>
      <SurfaceCard v-for="provider in providers" :key="provider.id" class="provider-card">
        <template #header><div class="provider-header"><div><strong>{{ provider.name }}</strong><div class="meta">{{ providerTypeLabel(provider.provider_type) }} · {{ provider.provider_name }}</div></div><div class="provider-actions"><el-tag :type="provider.enabled ? 'success' : 'info'">{{ provider.enabled ? '已启用' : '已停用' }}</el-tag><el-button link type="primary" @click="openEditProvider(provider)">编辑</el-button><el-button link type="danger" :loading="deletingProviderId === provider.id" :disabled="!!deletingProviderId" @click="requestDeleteProvider(provider)">删除</el-button></div></div></template>
        <el-descriptions :column="2" border><el-descriptions-item label="接口地址">{{ provider.endpoint || '未配置' }}</el-descriptions-item><el-descriptions-item label="凭据引用">{{ provider.credential_ref || '未配置' }}</el-descriptions-item></el-descriptions>
        <div class="profiles-header"><div><h2>模型配置</h2><p>通过 provider_id 关联当前提供方，模型配置使用后端返回的持久化 ID。</p></div><el-button size="small" type="primary" @click="openCreateProfile(provider.id)">创建模型配置</el-button></div>
        <StatePanel v-if="profileState(provider.id) !== 'success'" :state="profileState(provider.id) as any" :title="profileState(provider.id) === 'loading' ? '正在加载模型配置' : profileState(provider.id) === 'permission' ? '无权查看模型配置' : profileState(provider.id) === 'error' ? '模型配置加载失败' : '暂无模型配置'" :description="profileStateDescription(provider.id)" :action-label="profileState(provider.id) === 'error' || profileState(provider.id) === 'permission' ? '重新加载' : undefined" @action="loadProfiles(provider.id)" />
        <el-table v-else :data="profiles[provider.id]" border><el-table-column prop="name" label="名称" min-width="160" /><el-table-column label="类型" width="160"><template #default="{ row }">{{ modelTypeLabel(row.model_type) }}</template></el-table-column><el-table-column prop="model_name" label="模型" min-width="220" /><el-table-column prop="dimension" label="向量维度" width="110" /><el-table-column label="默认" width="90"><template #default="{ row }"><el-tag v-if="row.is_default" type="success">是</el-tag><span v-else>—</span></template></el-table-column><el-table-column label="状态" width="100"><template #default="{ row }"><el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '已启用' : '已停用' }}</el-tag></template></el-table-column><el-table-column label="操作" width="150"><template #default="{ row }"><el-button link type="primary" @click="openEditProfile(row as ModelProfile)">编辑</el-button><el-button link type="danger" :loading="deletingProfileId === row.id" :disabled="!!deletingProfileId" @click="requestDeleteProfile(row as ModelProfile)">删除</el-button></template></el-table-column></el-table>
      </SurfaceCard>
    </template>

    <el-dialog v-model="providerDialog" :title="editingProvider ? '编辑模型提供方' : '创建模型提供方'" width="620px" :close-on-click-modal="false">
      <el-form label-width="120px"><el-form-item label="名称" required><el-input v-model="providerForm.name" /></el-form-item><el-form-item label="提供方类型" required><el-input v-model="providerForm.provider_type" :disabled="!!editingProvider" /></el-form-item><el-form-item label="提供方名称" required><el-input v-model="providerForm.provider_name" :disabled="!!editingProvider" /></el-form-item><el-form-item label="接口地址"><el-input v-model="providerForm.endpoint" /></el-form-item><el-form-item label="凭据引用"><el-input v-model="providerForm.credential_ref" placeholder="仅填写引用，不填写密钥正文" /></el-form-item><el-form-item label="启用"><el-switch v-model="providerForm.enabled" /></el-form-item></el-form>
      <template #footer><el-button :disabled="providerSaving" @click="providerDialog=false">取消</el-button><el-button type="primary" :loading="providerSaving" @click="saveProvider">保存</el-button></template>
    </el-dialog>
    <el-dialog v-model="profileDialog" :title="editingProfile ? '编辑模型配置' : '创建模型配置'" width="620px" :close-on-click-modal="false">
      <el-form label-width="120px"><el-form-item label="名称" required><el-input v-model="profileForm.name" /></el-form-item><el-form-item label="类型" required><el-select v-model="profileForm.model_type" style="width:100%"><el-option label="对话模型" value="chat" /><el-option label="向量模型" value="embedding" /></el-select></el-form-item><el-form-item label="模型名称" required><el-input v-model="profileForm.model_name" /></el-form-item><el-form-item v-if="profileForm.model_type === 'embedding'" label="向量维度" required><el-input-number v-model="profileForm.dimension" :min="1" /></el-form-item><el-form-item label="默认"><el-switch v-model="profileForm.is_default" /></el-form-item><el-form-item label="启用"><el-switch v-model="profileForm.enabled" /></el-form-item></el-form>
      <template #footer><el-button :disabled="profileSaving" @click="profileDialog=false">取消</el-button><el-button type="primary" :loading="profileSaving" @click="saveProfile">保存</el-button></template>
    </el-dialog>
    <ConfirmDialog :model-value="!!confirmTarget" :title="confirmTarget?.kind === 'provider' ? '删除模型提供方' : '删除模型配置'" :description="confirmTarget?.kind === 'provider' ? '删除前请确认没有模型配置正在使用该提供方。删除后将无法继续通过该提供方运行模型。' : '删除后该模型配置将不能再用于后续模型选择，请确认继续。'" confirm-text="确认删除" :danger="true" :loading="!!deletingProviderId || !!deletingProfileId" @update:model-value="(value) => { if (!value) cancelDelete(); }" @confirm="confirmDelete" @cancel="cancelDelete" />
  </div>
</template>
<style scoped>
.page{padding:32px}.provider-card{margin-top:18px}.provider-header,.profiles-header{display:flex;justify-content:space-between;align-items:center;gap:16px}.provider-actions{display:flex;align-items:center;gap:6px}.meta{margin-top:4px;color:var(--ui-text-tertiary);font-size:12px}.profiles-header{margin:22px 0 12px}.profiles-header h2{margin:0;color:var(--ui-text-primary);font-size:16px}.profiles-header p{margin:4px 0 0;color:var(--ui-text-tertiary);font-size:12px}@media(max-width:700px){.page{padding:20px}.provider-header,.profiles-header{align-items:flex-start;flex-direction:column}.provider-actions{width:100%;flex-wrap:wrap}}
</style>
