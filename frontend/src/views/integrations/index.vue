<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { Connection, Plus, Refresh, Link, Bell, CircleCheck, Warning } from "@element-plus/icons-vue";
import PageHeader from "@/components/ui/PageHeader.vue";
import MetricCard from "@/components/ui/MetricCard.vue";
import StatePanel from "@/components/ui/StatePanel.vue";
import SurfaceCard from "@/components/ui/SurfaceCard.vue";
import ConfirmDialog from "@/components/ui/ConfirmDialog.vue";
import { integrationApi, type WebhookDestination, type WebhookSubscription } from "@/api/integrations";
import DeliveryConsole from "./DeliveryConsole.vue";
import IntegrationEventConsole from "./IntegrationEventConsole.vue";

const loading = ref(false);
const error = ref("");
const activeTab = ref("destinations");
const destinations = ref<WebhookDestination[]>([]);
const subscriptions = ref<WebhookSubscription[]>([]);
const destinationDialog = ref(false);
const subscriptionDialog = ref(false);
const destinationSaving = ref(false);
const subscriptionSaving = ref(false);
const destinationForm = reactive({ name: "", endpoint_url: "", secret_ref: "", headersText: "" });
const subscriptionForm = reactive({ destination_id: "", event_type: "", priority: 100 });
const enabledDestinations = computed(() => destinations.value.filter((item) => item.enabled).length);
const enabledSubscriptions = computed(() => subscriptions.value.filter((item) => item.enabled).length);
const eventTypeCount = computed(() => new Set(subscriptions.value.map((item) => item.event_type)).size);
const isPermissionError = computed(() => /^\s*403\b/.test(error.value));
const pageState = computed(() => loading.value ? "loading" : error.value ? "error" : "success");

function safeError(value: unknown, fallback: string) {
  if (value instanceof Error && value.message.trim() && !/^\s*\d{3}\b/.test(value.message)) return value.message.trim();
  return fallback;
}
async function loadData() {
  loading.value = true;
  error.value = "";
  try {
    const [destinationResponse, subscriptionResponse] = await Promise.all([integrationApi.destinations(), integrationApi.subscriptions()]);
    destinations.value = destinationResponse.data;
    subscriptions.value = subscriptionResponse.data;
  } catch (value) {
    destinations.value = [];
    subscriptions.value = [];
    error.value = safeError(value, "集成数据加载失败，请稍后重试");
  } finally { loading.value = false; }
}
function resetDestinationForm() { Object.assign(destinationForm, { name: "", endpoint_url: "", secret_ref: "", headersText: "" }); }
function openSubscriptionDialog() { subscriptionForm.destination_id = ""; subscriptionForm.event_type = ""; subscriptionForm.priority = 100; subscriptionDialog.value = true; }
async function createDestination() {
  if (destinationSaving.value) return;
  if (!destinationForm.name.trim() || !destinationForm.endpoint_url.trim()) { ElMessage.warning("请填写目标名称和目标地址"); return; }
  let headers: Record<string, string> = {};
  if (destinationForm.headersText.trim()) { try { headers = JSON.parse(destinationForm.headersText) as Record<string, string>; } catch { ElMessage.warning("请求头必须是合法的 JSON 对象"); return; } }
  destinationSaving.value = true;
  try {
    await integrationApi.createDestination({ name: destinationForm.name.trim(), endpoint_url: destinationForm.endpoint_url.trim(), secret_ref: destinationForm.secret_ref.trim() || undefined, headers });
    destinationDialog.value = false; resetDestinationForm(); await loadData(); ElMessage.success("投递目标已创建");
  } catch (value) { ElMessage.error(safeError(value, "投递目标创建失败，请稍后重试")); }
  finally { destinationSaving.value = false; }
}
async function createSubscription() {
  if (subscriptionSaving.value) return;
  if (!subscriptionForm.destination_id || !subscriptionForm.event_type.trim()) { ElMessage.warning("请选择投递目标并填写事件类型"); return; }
  subscriptionSaving.value = true;
  try {
    await integrationApi.createSubscription({ destination_id: subscriptionForm.destination_id, event_type: subscriptionForm.event_type.trim(), priority: subscriptionForm.priority });
    subscriptionDialog.value = false; await loadData(); ElMessage.success("事件订阅已创建");
  } catch (value) { ElMessage.error(safeError(value, "事件订阅创建失败，请稍后重试")); }
  finally { subscriptionSaving.value = false; }
}
function destinationName(id: string) { return destinations.value.find((item) => item.id === id)?.name || `未知投递目标（${id}）`; }
function formatTime(value: string) { const date = new Date(value); if (Number.isNaN(date.getTime())) return value; return date.toLocaleString("zh-CN", { hour12: false }); }
onMounted(loadData);
</script>

<template>
  <div class="integration-page">
    <PageHeader eyebrow="平台 / 系统集成" title="集成中心" description="将平台产生的可靠事件安全、稳定地发送到企业内部系统和业务服务。">
      <template #actions><el-button :icon="Refresh" :loading="loading" @click="loadData">刷新数据</el-button><el-button type="primary" :icon="Plus" @click="destinationDialog = true">新建投递目标</el-button></template>
    </PageHeader>

    <StatePanel v-if="pageState === 'loading'" state="loading" title="正在加载集成配置" description="正在读取当前租户的投递目标和事件订阅。" />
    <StatePanel v-else-if="pageState === 'error'" :state="isPermissionError ? 'permission' : 'error'" :title="isPermissionError ? '无权查看集成配置' : '集成配置加载失败'" :description="isPermissionError ? '当前账号没有访问集成配置的权限。' : error" action-label="重新加载" @action="loadData" />
    <template v-else>
      <div class="metric-grid"><MetricCard label="投递目标" :value="destinations.length" :description="`${enabledDestinations} 个已启用`" /><MetricCard label="事件订阅" :value="subscriptions.length" :description="`${enabledSubscriptions} 个已启用`" /><MetricCard label="事件类型" :value="eventTypeCount" description="当前订阅覆盖的不同事件类型" /></div>
      <el-alert title="安全提示" description="密钥只通过安全引用关联，页面不会保存或展示密钥明文；目标地址和请求头属于当前租户的集成配置。重新投递只会重新进入后端可靠投递流程，不会由浏览器直接请求目标地址。" type="info" :closable="false" show-icon class="security-note" />
      <SurfaceCard class="workspace-card">
        <el-tabs v-model="activeTab">
          <el-tab-pane name="destinations"><template #label><span class="tab-label"><Link /> 投递目标</span></template>
            <div class="toolbar"><div><strong>投递目标</strong><span>设置平台事件需要发送到哪里，以及对应的认证信息。</span></div><el-button type="primary" :icon="Plus" @click="destinationDialog = true">新建投递目标</el-button></div>
            <StatePanel v-if="!destinations.length" state="empty" title="暂无投递目标" description="当前租户还没有投递目标。创建目标后才能建立事件订阅。" action-label="新建投递目标" @action="destinationDialog = true" />
            <el-table v-else :data="destinations"><el-table-column prop="name" label="名称" min-width="180" /><el-table-column prop="endpoint_url" label="目标地址" min-width="300" show-overflow-tooltip /><el-table-column label="认证" width="120"><template #default="scope"><span class="security-state" :class="scope.row.secret_ref ? 'configured' : ''"><CircleCheck v-if="scope.row.secret_ref" /><Warning v-else />{{ scope.row.secret_ref ? "已配置" : "未配置" }}</span></template></el-table-column><el-table-column label="状态" width="110"><template #default="scope"><el-tag :type="scope.row.enabled ? 'success' : 'info'">{{ scope.row.enabled ? "已启用" : "已停用" }}</el-tag></template></el-table-column><el-table-column label="更新时间" min-width="180"><template #default="scope">{{ formatTime(scope.row.updated_at) }}</template></el-table-column></el-table>
          </el-tab-pane>
          <el-tab-pane name="subscriptions"><template #label><span class="tab-label"><Bell /> 事件订阅</span></template>
            <div class="toolbar"><div><strong>事件订阅</strong><span>按照事件类型，将平台产生的事件发送到指定投递目标。</span></div><el-button type="primary" :icon="Plus" :disabled="!destinations.length || subscriptionSaving" @click="openSubscriptionDialog">新建事件订阅</el-button></div>
            <StatePanel v-if="!subscriptions.length" state="empty" title="暂无事件订阅" description="当前租户还没有事件订阅。创建订阅时必须显式选择已有投递目标。" :action-label="destinations.length ? '新建事件订阅' : undefined" @action="openSubscriptionDialog" />
            <el-table v-else :data="subscriptions"><el-table-column prop="event_type" label="事件类型" min-width="240" /><el-table-column label="投递目标" min-width="180"><template #default="scope">{{ destinationName(scope.row.destination_id) }}</template></el-table-column><el-table-column prop="priority" label="优先级" width="110" /><el-table-column label="状态" width="110"><template #default="scope"><el-tag :type="scope.row.enabled ? 'success' : 'info'">{{ scope.row.enabled ? "已启用" : "已停用" }}</el-tag></template></el-table-column><el-table-column label="更新时间" min-width="180"><template #default="scope">{{ formatTime(scope.row.updated_at) }}</template></el-table-column></el-table>
            <div v-if="!destinations.length" class="empty-guidance"><Warning /> <span>请先创建至少一个投递目标，再建立事件订阅。</span></div>
          </el-tab-pane>
          <el-tab-pane name="events"><template #label><span class="tab-label"><Connection /> 事件观察</span></template><IntegrationEventConsole /></el-tab-pane>
          <el-tab-pane name="deliveries"><template #label><span class="tab-label"><Connection /> 投递管理</span></template><DeliveryConsole /></el-tab-pane>
        </el-tabs>
      </SurfaceCard>
    </template>

    <el-dialog v-model="destinationDialog" title="新建投递目标" width="560px" :close-on-click-modal="false">
      <el-form label-position="top"><el-form-item label="名称" required><el-input v-model="destinationForm.name" placeholder="例如：生产告警系统" /></el-form-item><el-form-item label="目标地址" required><el-input v-model="destinationForm.endpoint_url" placeholder="https://example.com/webhooks/agent" /></el-form-item><el-form-item label="密钥引用"><el-input v-model="destinationForm.secret_ref" placeholder="仅填写密钥引用，不要填写密钥明文" /></el-form-item><el-form-item label="自定义请求头"><el-input v-model="destinationForm.headersText" type="textarea" :rows="4" placeholder='{"X-Tenant": "production"}' /></el-form-item></el-form>
      <template #footer><el-button :disabled="destinationSaving" @click="destinationDialog = false">取消</el-button><el-button type="primary" :loading="destinationSaving" @click="createDestination">创建</el-button></template>
    </el-dialog>
    <el-dialog v-model="subscriptionDialog" title="新建事件订阅" width="520px" :close-on-click-modal="false">
      <el-form label-position="top"><el-form-item label="投递目标" required><el-select v-model="subscriptionForm.destination_id" style="width: 100%"><el-option v-for="item in destinations" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item><el-form-item label="事件类型" required><el-input v-model="subscriptionForm.event_type" placeholder="例如：workflow.execution.completed" /></el-form-item><el-form-item label="优先级"><el-input-number v-model="subscriptionForm.priority" :min="0" :max="10000" /></el-form-item></el-form>
      <template #footer><el-button :disabled="subscriptionSaving" @click="subscriptionDialog = false">取消</el-button><el-button type="primary" :loading="subscriptionSaving" @click="createSubscription">创建</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.integration-page{min-height:100%;padding:30px 32px 48px}.metric-grid,.workspace-card,.security-note{max-width:1240px;margin-left:auto;margin-right:auto}.metric-grid{margin-bottom:14px;display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.security-note{margin-bottom:14px}.workspace-card{border-color:var(--ui-border-default)}.toolbar{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:18px}.toolbar div{display:grid;gap:4px}.toolbar strong{color:var(--ui-text-primary);font-size:14px}.toolbar span{color:var(--ui-text-tertiary);font-size:12px}.tab-label{display:inline-flex;align-items:center;gap:6px}.tab-label svg{width:14px;height:14px}.empty-guidance{display:flex;align-items:center;gap:7px;margin-top:12px;padding:10px 12px;border:1px dashed var(--ui-border-default);border-radius:8px;color:var(--ui-text-secondary);background:var(--ui-bg-subtle);font-size:12px}.empty-guidance svg{width:14px;height:14px}.security-state{display:inline-flex;align-items:center;gap:4px;color:var(--ui-text-tertiary);font-size:12px}.security-state.configured{color:var(--ui-color-success-600)}.security-state svg{width:13px;height:13px}@media(max-width:760px){.integration-page{padding:20px 14px 36px}.metric-grid{grid-template-columns:1fr}.toolbar{align-items:stretch;flex-direction:column}}
</style>
