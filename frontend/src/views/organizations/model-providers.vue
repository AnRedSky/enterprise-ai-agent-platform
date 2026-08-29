<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  createModelProfile,
  createModelProvider,
  deleteModelProfile,
  deleteModelProvider,
  listModelProfiles,
  listModelProviders,
  updateModelProfile,
  updateModelProvider,
  type ModelProfile,
  type ModelProfileCreatePayload,
  type ModelProvider,
  type ModelProviderCreatePayload,
  type ModelProviderUpdatePayload,
} from "@/api/modelProviders";

const route = useRoute();
const router = useRouter();
const organizationId = String(route.params.id);
const providers = ref<ModelProvider[]>([]);
const profiles = ref<Record<string, ModelProfile[]>>({});
const loading = ref(false);
const error = ref("");
const saving = ref(false);
const providerDialog = ref(false);
const profileDialog = ref(false);
const editingProvider = ref<ModelProvider | null>(null);
const editingProfile = ref<ModelProfile | null>(null);
const selectedProviderId = ref("");

const providerForm = ref<ModelProviderCreatePayload>({ organization_id: organizationId, name: "", provider_type: "ollama", provider_name: "", endpoint: "", credential_ref: "", enabled: true, metadata: {} });
const profileForm = ref<ModelProfileCreatePayload>({ name: "", model_type: "chat", model_name: "", dimension: null, capabilities: {}, parameters: {}, enabled: true, is_default: false });
const profileList = computed(() => selectedProviderId.value ? profiles.value[selectedProviderId.value] ?? [] : []);

function resetProvider() {
  editingProvider.value = null;
  providerForm.value = { organization_id: organizationId, name: "", provider_type: "ollama", provider_name: "", endpoint: "", credential_ref: "", enabled: true, metadata: {} };
}
function resetProfile(providerId: string) {
  editingProfile.value = null;
  selectedProviderId.value = providerId;
  profileForm.value = { name: "", model_type: "chat", model_name: "", dimension: null, capabilities: {}, parameters: {}, enabled: true, is_default: false };
}

async function loadProfiles(providerId: string) {
  profiles.value[providerId] = await listModelProfiles(providerId);
}
async function load() {
  loading.value = true; error.value = "";
  try {
    providers.value = (await listModelProviders(organizationId)).items;
    await Promise.all(providers.value.map((provider) => loadProfiles(provider.id)));
  } catch (e) { error.value = e instanceof Error ? e.message : "模型提供方列表加载失败"; }
  finally { loading.value = false; }
}
function openCreateProvider() { resetProvider(); providerDialog.value = true; }
function openEditProvider(provider: ModelProvider) {
  editingProvider.value = provider;
  providerForm.value = { organization_id: organizationId, name: provider.name, provider_type: provider.provider_type, provider_name: provider.provider_name, endpoint: provider.endpoint ?? "", credential_ref: provider.credential_ref ?? "", enabled: provider.enabled, metadata: provider.metadata };
  providerDialog.value = true;
}
async function saveProvider() {
  if (!providerForm.value.name.trim() || !providerForm.value.provider_name.trim()) return;
  saving.value = true;
  try {
    if (editingProvider.value) await updateModelProvider(editingProvider.value.id, providerForm.value as ModelProviderUpdatePayload);
    else await createModelProvider(providerForm.value);
    providerDialog.value = false; await load(); ElMessage.success("模型提供方保存成功");
  } catch (e) { ElMessage.error(e instanceof Error ? e.message : "模型提供方保存失败"); }
  finally { saving.value = false; }
}
async function removeProvider(provider: ModelProvider) {
  try { await ElMessageBox.confirm("删除模型提供方前，请先确认没有模型配置正在使用它。", "删除模型提供方", { type: "warning" }); await deleteModelProvider(provider.id); await load(); ElMessage.success("模型提供方已删除"); }
  catch (e) { if (e !== "cancel" && e !== "close") ElMessage.error(e instanceof Error ? e.message : "模型提供方删除失败"); }
}
function openCreateProfile(providerId: string) { resetProfile(providerId); profileDialog.value = true; }
function openEditProfile(profile: ModelProfile) {
  editingProfile.value = profile; selectedProviderId.value = profile.provider_id;
  profileForm.value = { name: profile.name, model_type: profile.model_type, model_name: profile.model_name, dimension: profile.dimension, capabilities: profile.capabilities, parameters: profile.parameters, enabled: profile.enabled, is_default: profile.is_default };
  profileDialog.value = true;
}
function editProfileFromTableRow(row: unknown) {
  openEditProfile(row as ModelProfile);
}
async function saveProfile() {
  if (!profileForm.value.name.trim() || !profileForm.value.model_name.trim() || !selectedProviderId.value) return;
  const payload = { ...profileForm.value, dimension: profileForm.value.model_type === "embedding" ? profileForm.value.dimension : null };
  saving.value = true;
  try {
    if (editingProfile.value) await updateModelProfile(editingProfile.value.id, payload);
    else await createModelProfile(selectedProviderId.value, payload);
    profileDialog.value = false; await loadProfiles(selectedProviderId.value); ElMessage.success("模型配置保存成功");
  } catch (e) { ElMessage.error(e instanceof Error ? e.message : "模型配置保存失败"); }
  finally { saving.value = false; }
}
async function removeProfile(profile: ModelProfile) {
  try { await ElMessageBox.confirm("删除模型配置后，不能再用于运行记录或评估。", "删除模型配置", { type: "warning" }); await deleteModelProfile(profile.id); await loadProfiles(profile.provider_id); ElMessage.success("模型配置已删除"); }
  catch (e) { if (e !== "cancel" && e !== "close") ElMessage.error(e instanceof Error ? e.message : "模型配置删除失败"); }
}
function removeProfileFromTableRow(row: unknown) {
  void removeProfile(row as ModelProfile);
}

onMounted(load);
</script>

<template>
  <div class="page">
    <div class="header"><div><el-button link @click="router.push(`/organizations/${organizationId}`)">← 返回组织</el-button><h1>模型提供方与模型配置</h1><p>管理组织范围内的模型提供方和对话、向量模型配置。凭据仅显示引用，不显示密钥。</p></div><el-button type="primary" @click="openCreateProvider">创建模型提供方</el-button></div>
    <el-alert v-if="error" :title="error" type="error" show-icon />
    <el-empty v-if="!loading && !providers.length" description="暂无模型提供方。" />
    <el-card v-for="provider in providers" :key="provider.id" v-loading="loading" class="provider-card">
      <template #header><div class="provider-header"><div><strong>{{ provider.name }}</strong><div class="meta">{{ provider.provider_type }} · {{ provider.provider_name }}</div></div><div><el-tag :type="provider.enabled ? 'success' : 'info'">{{ provider.enabled ? '已启用' : '已停用' }}</el-tag><el-button link type="primary" @click="openEditProvider(provider)">编辑</el-button><el-button link type="danger" @click="removeProvider(provider)">删除</el-button></div></div></template>
      <el-descriptions :column="2" border><el-descriptions-item label="接口地址">{{ provider.endpoint || '未配置' }}</el-descriptions-item><el-descriptions-item label="凭据引用">{{ provider.credential_ref || '未配置' }}</el-descriptions-item></el-descriptions>
      <div class="profiles-header"><h2>模型配置</h2><el-button size="small" type="primary" @click="openCreateProfile(provider.id)">创建模型配置</el-button></div>
      <el-table :data="profiles[provider.id] ?? []" border><el-table-column prop="name" label="名称" min-width="160" /><el-table-column prop="model_type" label="类型" width="120" /><el-table-column prop="model_name" label="模型" min-width="220" /><el-table-column prop="dimension" label="Dimension" width="110" /><el-table-column label="默认" width="90"><template #default="{ row }"><el-tag v-if="row.is_default" type="success">是</el-tag></template></el-table-column><el-table-column label="状态" width="100"><template #default="{ row }"><el-tag :type="row.enabled ? 'success' : 'info'">{{ row.enabled ? '已启用' : '已停用' }}</el-tag></template></el-table-column><el-table-column label="操作" width="150"><template #default="{ row }"><el-button link type="primary" @click="editProfileFromTableRow(row)">编辑</el-button><el-button link type="danger" @click="removeProfileFromTableRow(row)">删除</el-button></template></el-table-column></el-table>
    </el-card>

    <el-dialog v-model="providerDialog" :title="editingProvider ? '编辑模型提供方' : '创建模型提供方'" width="620px"><el-form label-width="120px"><el-form-item label="名称" required><el-input v-model="providerForm.name" /></el-form-item><el-form-item label="提供方类型" required><el-input v-model="providerForm.provider_type" /></el-form-item><el-form-item label="提供方名称" required><el-input v-model="providerForm.provider_name" /></el-form-item><el-form-item label="接口地址"><el-input v-model="providerForm.endpoint" /></el-form-item><el-form-item label="凭据引用"><el-input v-model="providerForm.credential_ref" placeholder="仅填写密钥或环境变量的引用" /></el-form-item><el-form-item label="启用"><el-switch v-model="providerForm.enabled" /></el-form-item></el-form><template #footer><el-button @click="providerDialog=false">取消</el-button><el-button type="primary" :loading="saving" @click="saveProvider">保存</el-button></template></el-dialog>
    <el-dialog v-model="profileDialog" :title="editingProfile ? '编辑模型配置' : '创建模型配置'" width="620px"><el-form label-width="120px"><el-form-item label="名称" required><el-input v-model="profileForm.name" /></el-form-item><el-form-item label="类型" required><el-select v-model="profileForm.model_type" style="width:100%"><el-option label="对话模型" value="chat" /><el-option label="向量模型" value="embedding" /></el-select></el-form-item><el-form-item label="模型名称" required><el-input v-model="profileForm.model_name" /></el-form-item><el-form-item v-if="profileForm.model_type === 'embedding'" label="Dimension" required><el-input-number v-model="profileForm.dimension" :min="1" /></el-form-item><el-form-item label="默认"><el-switch v-model="profileForm.is_default" /></el-form-item><el-form-item label="启用"><el-switch v-model="profileForm.enabled" /></el-form-item></el-form><template #footer><el-button @click="profileDialog=false">取消</el-button><el-button type="primary" :loading="saving" @click="saveProfile">保存</el-button></template></el-dialog>
  </div>
</template>

<style scoped>.page{padding:32px}.header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:20px}.header h1{margin:8px 0}.header p,.meta{color:#667085}.provider-card{margin-top:18px}.provider-header,.profiles-header{display:flex;justify-content:space-between;align-items:center}.provider-header>div:last-child{display:flex;align-items:center;gap:6px}.profiles-header{margin:22px 0 12px}.profiles-header h2{margin:0}</style>
