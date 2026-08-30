<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
const expanded = ref(true);
const checks = computed(() => [
  { label: "已发布版本", done: true, description: "仅使用已发布版本进入真实调试" },
  { label: "运行上下文", done: true, description: "请求、会话、执行与链路标识会随调试过程保留" },
  { label: "失败可诊断", done: true, description: "失败后可直接进入运行中心查看 Trace 与 Audit" },
]);
function openRuntime() { void router.push({ path: "/runtime", query: { source: "agent-debug" } }); }
</script>

<template>
  <section class="debug-panel" aria-label="智能体对话调试体验">
    <div class="debug-head">
      <div><span class="eyebrow">P1 对话调试</span><h2>生产级调试上下文</h2><p>对话调试不是孤立聊天窗口：每次请求都保留运行上下文，便于从结果直接进入诊断链路。</p></div>
      <div class="actions"><el-tag type="success" effect="plain">可诊断</el-tag><el-button text @click="expanded = !expanded">{{ expanded ? "收起" : "展开" }}</el-button></div>
    </div>
    <div v-if="expanded" class="debug-body">
      <div class="check-list"><div v-for="item in checks" :key="item.label" class="check-item"><span class="check-mark">✓</span><div><strong>{{ item.label }}</strong><small>{{ item.description }}</small></div></div></div>
      <div class="debug-route"><div><strong>调试 → 运行中心</strong><span>请求标识 / 链路追踪标识 / 会话标识 / 执行标识</span></div><el-button type="primary" plain size="small" @click="openRuntime">查看运行中心</el-button></div>
    </div>
  </section>
</template>

<style scoped>
.debug-panel{margin:20px 32px 0;padding:18px 22px;border:1px solid #e4e7ed;border-radius:12px;background:#fff}.debug-head{display:flex;justify-content:space-between;gap:20px}.eyebrow{font-size:10px;color:#667085;font-weight:700;letter-spacing:.08em}.debug-head h2{margin:4px 0;font-size:17px;color:#1d2939}.debug-head p{margin:0;color:#667085;font-size:12px}.actions{display:flex;align-items:flex-start;gap:8px}.debug-body{margin-top:16px}.check-list{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.check-item{display:flex;gap:9px;padding:12px;border:1px solid #eaecf0;border-radius:9px;background:#fcfcfd}.check-mark{display:grid;place-items:center;width:20px;height:20px;border-radius:50%;background:#ecfdf3;color:#027a48;font-size:11px}.check-item strong,.check-item small{display:block}.check-item strong{font-size:12px;color:#344054}.check-item small{margin-top:3px;color:#667085;font-size:10px;line-height:1.5}.debug-route{display:flex;justify-content:space-between;align-items:center;margin-top:10px;padding:12px 14px;border-radius:9px;background:#f8fafc}.debug-route strong,.debug-route span{display:block}.debug-route strong{font-size:12px;color:#344054}.debug-route span{margin-top:3px;color:#667085;font-size:10px}@media(max-width:800px){.debug-panel{margin:14px}.debug-head{flex-direction:column}.check-list{grid-template-columns:1fr}.debug-route{align-items:flex-start;gap:10px;flex-direction:column}}
</style>
