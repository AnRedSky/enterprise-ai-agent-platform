<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { Connection, Plus, Refresh, Link, Bell } from "@element-plus/icons-vue";
import { integrationApi, type WebhookDestination, type WebhookSubscription } from "@/api/integrations";

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

async function loadData() {
  loading.value = true;
  try {
    const [destinationResponse, subscriptionResponse] = await Promise.all([
      integrationApi.destinations(),
      integrationApi.subscriptions(),
    ]);
    destinations.value = destinationResponse.data;
    subscriptions.value = subscriptionResponse.data;
    if (!subscriptionForm.destination_id && destinations.value[0]) subscriptionForm.destination_id = destinations.value[0].id;
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "集成数据加载失败");
  } finally {
    loading.value = false;
  }
}

function resetDestinationForm() {
  destinationForm.name = "";
  destinationForm.endpoint_url = "";
  destinationForm.secret_ref = "";
  destinationForm.headersText = "";
}

async function createDestination() {
  if (!destinationForm.name.trim() || !destinationForm.endpoint_url.trim()) {
    ElMessage.warning("请填写 Destination 名称和 Endpoint URL");
    return;
  }
  let headers: Record<string, string> = {};
  if (destinationForm.headersText.trim()) {
    try {
      headers = JSON.parse(destinationForm.headersText) as Record<string, string>;
    } catch {
      ElMessage.warning("Headers 必须是合法 JSON 对象");
      return;
    }
  }
  try {
    await integrationApi.createDestination({
      name: destinationForm.name.trim(),
      endpoint_url: destinationForm.endpoint_url.trim(),
      secret_ref: destinationForm.secret_ref.trim() || undefined,
      headers,
    });
    destinationDialog.value = false;
    resetDestinationForm();
    await loadData();
    ElMessage.success("Destination 已创建");
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "Destination 创建失败");
  }
}

async function createSubscription() {
  if (!subscriptionForm.destination_id || !subscriptionForm.event_type.trim()) {
    ElMessage.warning("请选择 Destination 并填写 Event Type");
    return;
  }
  try {
    await integrationApi.createSubscription({
      destination_id: subscriptionForm.destination_id,
      event_type: subscriptionForm.event_type.trim(),
      priority: subscriptionForm.priority,
    });
    subscriptionDialog.value = false;
    subscriptionForm.event_type = "";
    await loadData();
    ElMessage.success("Subscription 已创建");
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "Subscription 创建失败");
  }
}

function destinationName(id: string) {
  return destinations.value.find((item) => item.id === id)?.name || id;
}

onMounted(loadData);
</script>

<template>
  <div class="integration-page">
    <div class="page-heading">
      <div>
        <div class="eyebrow">INTEGRATIONS</div>
        <h1>集成中心</h1>
        <p>统一管理企业事件出站、Webhook Destination 与 Subscription。</p>
      </div>
      <el-button :icon="Refresh" :loading="loading" @click="loadData">刷新</el-button>
    </div>

    <div class="metric-grid">
      <div class="metric-card"><span>Destinations</span><strong>{{ destinations.length }}</strong><small>{{ enabledDestinations }} 个已启用</small></div>
      <div class="metric-card"><span>Subscriptions</span><strong>{{ subscriptions.length }}</strong><small>{{ enabledSubscriptions }} 个已启用</small></div>
      <div class="metric-card"><span>出站模式</span><strong>Webhook</strong><small>HTTP Event Delivery</small></div>
    </div>

    <el-card class="workspace-card" shadow="never">
      <el-tabs v-model="activeTab">
        <el-tab-pane name="destinations">
          <template #label><span class="tab-label"><Link /> Destinations</span></template>
          <div class="toolbar"><div><strong>出站目标</strong><span>Endpoint、Secret 引用与自定义 Headers</span></div><el-button type="primary" :icon="Plus" @click="destinationDialog = true">新建 Destination</el-button></div>
          <el-table v-loading="loading" :data="destinations" empty-text="暂无 Destination">
            <el-table-column prop="name" label="名称" min-width="180" />
            <el-table-column prop="endpoint_url" label="Endpoint" min-width="300" show-overflow-tooltip />
            <el-table-column label="认证引用" width="150"><template #default="scope">{{ scope.row.secret_ref ? "已配置" : "未配置" }}</template></el-table-column>
            <el-table-column label="状态" width="110"><template #default="scope"><el-tag :type="scope.row.enabled ? "success" : "info"">{{ scope.row.enabled ? "已启用" : "已停用" }}</el-tag></template></el-table-column>
            <el-table-column prop="updated_at" label="更新时间" min-width="180" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane name="subscriptions">
          <template #label><span class="tab-label"><Bell /> Subscriptions</span></template>
          <div class="toolbar"><div><strong>事件订阅</strong><span>按 Event Type 将 Durable Event 投递到指定目标</span></div><el-button type="primary" :icon="Plus" :disabled="!destinations.length" @click="subscriptionDialog = true">新建 Subscription</el-button></div>
          <el-table v-loading="loading" :data="subscriptions" empty-text="暂无 Subscription">
            <el-table-column prop="event_type" label="Event Type" min-width="220" />
            <el-table-column label="Destination" min-width="180"><template #default="scope">{{ destinationName(scope.row.destination_id) }}</template></el-table-column>
            <el-table-column prop="priority" label="优先级" width="110" />
            <el-table-column label="状态" width="110"><template #default="scope"><el-tag :type="scope.row.enabled ? "success" : "info"">{{ scope.row.enabled ? "已启用" : "已停用" }}</el-tag></template></el-table-column>
            <el-table-column prop="updated_at" label="更新时间" min-width="180" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="destinationDialog" title="新建 Webhook Destination" width="560px" @closed="resetDestinationForm">
      <el-form label-position="top">
        <el-form-item label="名称" required><el-input v-model="destinationForm.name" placeholder="例如：生产告警系统" /></el-form-item>
        <el-form-item label="Endpoint URL" required><el-input v-model="destinationForm.endpoint_url" placeholder="https://example.com/webhooks/agent" /></el-form-item>
        <el-form-item label="Secret 引用"><el-input v-model="destinationForm.secret_ref" placeholder="仅填写 Secret 引用，不填写 Secret 明文" /></el-form-item>
        <el-form-item label="自定义 Headers"><el-input v-model="destinationForm.headersText" type="textarea" :rows="4" placeholder='{"X-Tenant": "production"}' /></el-form-item>
      </el-form>
      <template #footer><el-button @click="destinationDialog = false">取消</el-button><el-button type="primary" @click="createDestination">创建</el-button></template>
    </el-dialog>

    <el-dialog v-model="subscriptionDialog" title="新建 Event Subscription" width="520px">
      <el-form label-position="top">
        <el-form-item label="Destination" required><el-select v-model="subscriptionForm.destination_id" style="width: 100%"><el-option v-for="item in destinations" :key="item.id" :label="item.name" :value="item.id" /></el-select></el-form-item>
        <el-form-item label="Event Type" required><el-input v-model="subscriptionForm.event_type" placeholder="例如：runtime.execution.completed" /></el-form-item>
        <el-form-item label="优先级"><el-input-number v-model="subscriptionForm.priority" :min="0" :max="10000" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="subscriptionDialog = false">取消</el-button><el-button type="primary" @click="createSubscription">创建</el-button></template>
    </el-dialog>
  </div>
</template>

<style scoped>
.integration-page { min-height: 100%; padding: 30px 32px 48px; background: #f7f8fa; }
.page-heading { max-width: 1240px; margin: 0 auto 24px; display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; }
.eyebrow { color: #98a2b3; font-size: 11px; font-weight: 700; letter-spacing: .12em; }
h1 { margin: 5px 0 7px; color: #101828; font-size: 28px; letter-spacing: -.02em; }
.page-heading p { margin: 0; color: #667085; font-size: 13px; }
.metric-grid { max-width: 1240px; margin: 0 auto 20px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.metric-card { padding: 18px 20px; border: 1px solid #eaecf0; border-radius: 12px; background: #fff; }
.metric-card span, .metric-card small { display: block; color: #667085; font-size: 12px; }
.metric-card strong { display: block; margin: 7px 0 4px; color: #101828; font-size: 24px; }
.workspace-card { max-width: 1240px; margin: 0 auto; border-color: #eaecf0; }
.toolbar { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 18px; }
.toolbar div { display: grid; gap: 3px; }
.toolbar strong { color: #344054; font-size: 14px; }
.toolbar span { color: #98a2b3; font-size: 12px; }
.tab-label { display: inline-flex; align-items: center; gap: 6px; }
.tab-label svg { width: 14px; height: 14px; }
@media (max-width: 760px) { .integration-page { padding: 20px 14px 36px; } .metric-grid { grid-template-columns: 1fr; } .page-heading, .toolbar { align-items: stretch; flex-direction: column; } }
</style>
