<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { Connection, Plus, Refresh, Link, Bell, CircleCheck, Warning } from "@element-plus/icons-vue";
import { integrationApi, type WebhookDestination, type WebhookSubscription } from "@/api/integrations";
import DeliveryConsole from "./DeliveryConsole.vue";

const loading = ref(false);
const activeTab = ref("destinations");
const destinations = ref<WebhookDestination[]>([]);
const subscriptions = ref<WebhookSubscription[]>([]);
const destinationDialog = ref(false);
const subscriptionDialog = ref(false);
const destinationForm = reactive({ name: "", endpoint_url: "", secret_ref: "", headersText: "" });
const subscriptionForm = reactive({ destination_id: "", event_type: "", priority: 100 });
const enabledDestinations = computed(() => destinations.value.filter((item) => item.enabled).length);
const enabledSubscriptions = computed(() => subscriptions.value.filter((item) => item.enabled).length);
const eventTypeCount = computed(() => new Set(subscriptions.value.map((item) => item.event_type)).size);

async function loadData() {
  loading.value = true;
  try {
    const [destinationResponse, subscriptionResponse] = await Promise.all([integrationApi.destinations(), integrationApi.subscriptions()]);
    destinations.value = destinationResponse.data;
    subscriptions.value = subscriptionResponse.data;
    if (!subscriptionForm.destination_id && destinations.value[0]) subscriptionForm.destination_id = destinations.value[0].id;
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "集成数据加载失败");
  } finally { loading.value = false; }
}
function resetDestinationForm() { Object.assign(destinationForm, { name: "", endpoint_url: "", secret_ref: "", headersText: "" }); }
async function createDestination() {
  if (!destinationForm.name.trim() || !destinationForm.endpoint_url.trim()) { ElMessage.warning("请填写 Destination 名称和 Endpoint URL"); return; }
  let headers: Record<string, string> = {};
  if (destinationForm.headersText.trim()) { try { headers = JSON.parse(destinationForm.headersText) as Record<string, string>; } catch { ElMessage.warning("Headers 必须是合法 JSON 对象"); return; } }
  try {
    await integrationApi.createDestination({ name: destinationForm.name.trim(), endpoint_url: destinationForm.endpoint_url.trim(), secret_ref: destinationForm.secret_ref.trim() || undefined, headers });
    destinationDialog.value = false; resetDestinationForm(); await loadData(); ElMessage.success("Destination 已创建");
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : "Destination 创建失败"); }
}
async function createSubscription() {
  if (!subscriptionForm.destination_id || !subscriptionForm.event_type.trim()) { ElMessage.warning("请选择 Destination 并填写 Event Type"); return; }
  try {
    await integrationApi.createSubscription({ destination_id: subscriptionForm.destination_id, event_type: subscriptionForm.event_type.trim(), priority: subscriptionForm.priority });
    subscriptionDialog.value = false; subscriptionForm.event_type = ""; await loadData(); ElMessage.success("Subscription 已创建");
  } catch (error) { ElMessage.error(error instanceof Error ? error.message : "Subscription 创建失败"); }
}
function destinationName(id: string) { return destinations.value.find((item) => item.id === id)?.name || id; }
function formatTime(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", { hour12: false });
}
onMounted(loadData);
</script>

<template>
  <div class="integration-page">
    <div class="page-heading">
      <div class="heading-copy"><div class="eyebrow">PLATFORM / INTEGRATIONS</div><h1>集成中心</h1><p>把 Durable Integration Event 可靠连接到企业内部系统、告警平台和业务服务。</p></div>
      <el-button :icon="Refresh" :loading="loading" @click="loadData">刷新数据</el-button>
    </div>

    <div class="metric-grid">
      <div class="metric-card"><div class="metric-icon"><Link /></div><div><span>出站目标</span><strong>{{ destinations.length }}</strong><small><CircleCheck /> {{ enabledDestinations }} 个已启用</small></div></div>
      <div class="metric-card"><div class="metric-icon"><Bell /></div><div><span>事件订阅</span><strong>{{ subscriptions.length }}</strong><small><CircleCheck /> {{ enabledSubscriptions }} 个已启用</small></div></div>
      <div class="metric-card"><div class="metric-icon"><Connection /></div><div><span>事件类型</span><strong>{{ eventTypeCount }}</strong><small>当前订阅覆盖的唯一 Event Type</small></div></div>
    </div>

    <el-alert title="安全提示" description="Secret 仅通过 Secret 引用关联，页面不会保存或展示 Secret 明文；Endpoint 与 Header 配置属于租户级集成配置。Replay 仅调用后端可靠投递流程，不在浏览器直接请求目标 Endpoint。" type="info" :closable="false" show-icon class="security-note" />

    <el-card class="workspace-card" shadow="never">
      <el-tabs v-model="activeTab">
        <el-tab-pane name="destinations">
          <template #label><span class="tab-label"><Link /> 出站目标</span></template>
          <div class="toolbar"><div><strong>Webhook Destinations</strong><span>定义平台事件最终投递的位置与认证引用。</span></div><el-button type="primary" :icon="Plus" @click="destinationDialog = true">新建 Destination</el-button></div>
          <el-table v-loading="loading" :data="destinations" empty-text="暂无 Destination">
            <el-table-column prop="name" label="名称" min-width="180" />
            <el-table-column prop="endpoint_url" label="Endpoint" min-width="300" show-overflow-tooltip />
            <el-table-column label="认证" width="120"><template #default="scope"><span class="security-state" :class="scope.row.secret_ref ? 'configured' : ''"><CircleCheck v-if="scope.row.secret_ref" /><Warning v-else />{{ scope.row.secret_ref ? "已配置" : "未配置" }}</span></template></el-table-column>
            <el-table-column label="状态" width="110"><template #default="scope"><el-tag :type="scope.row.enabled ? 'success' : 'info'">{{ scope.row.enabled ? "已启用" : "已停用" }}</el-tag></template></el-table-column>
            <el-table-column label="更新时间" min-width="180"><template #default="scope">{{ formatTime(scope.row.updated_at) }}</template></el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane name="subscriptions">
          <template #label><span class="tab-label"><Bell /> 事件订阅</span></template>
          <div class="toolbar"><div><strong>Event Subscriptions</strong><span>按 Event Type 将 Durable Event 投递到指定 Destination。</span></div><el-button type="primary" :icon="Plus" :disabled="!destinations.length" @click="subscriptionDialog = true">新建 Subscription</el-button></div>
          <el-table v-loading="loading" :data="subscriptions" empty-text="暂无 Subscription">
            <el-table-column prop="event_type" label="Event Type" min-width="240" />
            <el-table-column label="Destination" min-width="180"><template #default="scope">{{ destinationName(scope.row.destination_id) }}</template></el-table-column>
            <el-table-column prop="priority" label="优先级" width="110" />
            <el-table-column label="状态" width="110"><template #default="scope"><el-tag :type="scope.row.enabled ? 'success' : 'info'">{{ scope.row.enabled ? "已启用" : "已停用" }}</el-tag></template></el-table-column>
            <el-table-column label="更新时间" min-width="180"><template #default="scope">{{ formatTime(scope.row.updated_at) }}</template></el-table-column>
          </el-table>
          <div v-if="!destinations.length" class="empty-guidance"><Warning /> <span>请先创建至少一个 Destination，再建立事件订阅。</span></div>
        </el-tab-pane>
        <el-tab-pane name="deliveries">
          <template #label><span class="tab-label"><Connection /> 投递运维</span></template>
          <DeliveryConsole />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="destinationDialog" title="新建 Webhook Destination" width="560px" @closed="resetDestinationForm">
      <el-form label-position="top"><el-form-item label="名称" required><el-input v-model="destinationForm.name" placeholder="例如：生产告警系统" /></el-form-item><el-form-item label="Endpoint URL" required><el-input v-model="destinationForm.endpoint_url" placeholder="https://example.com/webhooks/agent" /></el-form-item><el-form-item label="Secret 引用"><el-input v-model="destinationForm.secret_ref" placeholder="仅填写 Secret 引用，不填写 Secret 明文" /></el-form-item><el-form-item label="自定义 Headers"><el-input v-model="destinationForm.headersText" type="textarea" :rows="4" placeholder='{"X-Tenant": "production"}' /></el-form-item></el-form>
      <template #footer><el-button @click="destinationDialog = false">取消</el-button><el-button type="primary" @click="createDestination">创建</el-button></template>
    </el-dialog>
    <el-dialog v-model="subscriptionDialog" title="新建 Event Subscription" width="520px">
      <el-form label-position="top"><el-form-item label="Destination" required><el-select v-model="subscriptionForm.destination_id" style="width: 100%"><el-option v-for="item in destinations" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item><el-form-item label="Event Type" required><el-input v-model="subscriptionForm.event_type" placeholder="例如：workflow.execution.completed" /></el-form-item><el-form-item label="优先级"><el-input-number v-model="subscriptionForm.priority" :min="0" :max="10000" /></el-form-item></el-form>
      <template #footer><el-button @click="subscriptionDialog = false">取消</el-button><el-button type="primary" @click="createSubscription">创建</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.integration-page{min-height:100%;padding:30px 32px 48px;background:#f7f8fa}.page-heading,.metric-grid,.workspace-card,.security-note{max-width:1240px;margin-left:auto;margin-right:auto}.page-heading{margin-bottom:20px;display:flex;align-items:flex-start;justify-content:space-between;gap:20px}.eyebrow{color:#98a2b3;font-size:10px;font-weight:700;letter-spacing:.13em}.heading-copy h1{margin:5px 0 7px;color:#101828;font-size:28px;letter-spacing:-.02em}.heading-copy p{margin:0;color:#667085;font-size:13px}.metric-grid{margin-bottom:14px;display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.metric-card{min-height:92px;padding:16px 18px;border:1px solid #eaecf0;border-radius:12px;background:#fff;display:flex;align-items:center;gap:13px}.metric-icon{width:38px;height:38px;display:grid;place-items:center;border-radius:9px;background:#f2f4f7;color:#344054}.metric-card span{display:block;color:#667085;font-size:11px}.metric-card strong{display:block;margin:3px 0;color:#101828;font-size:22px}.metric-card small{display:flex;align-items:center;gap:4px;color:#98a2b3;font-size:10px}.metric-card small svg{width:11px;height:11px}.security-note{margin-bottom:14px}.workspace-card{border-color:#eaecf0}.toolbar{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:18px}.toolbar div{display:grid;gap:4px}.toolbar strong{color:#344054;font-size:14px}.toolbar span{color:#98a2b3;font-size:12px}.tab-label{display:inline-flex;align-items:center;gap:6px}.tab-label svg{width:14px;height:14px}.empty-guidance{display:flex;align-items:center;gap:7px;margin-top:12px;padding:10px 12px;border:1px dashed #d0d5dd;border-radius:8px;color:#667085;background:#f8fafc;font-size:12px}.empty-guidance svg{width:14px;height:14px}.security-state{display:inline-flex;align-items:center;gap:4px;color:#98a2b3;font-size:12px}.security-state.configured{color:#67c23a}.security-state svg{width:13px;height:13px}@media(max-width:760px){.integration-page{padding:20px 14px 36px}.metric-grid{grid-template-columns:1fr}.page-heading,.toolbar{align-items:stretch;flex-direction:column}}
</style>
