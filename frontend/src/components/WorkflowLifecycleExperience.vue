<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();
const status = computed(() => typeof route.query.lifecycle === "string" ? route.query.lifecycle : "draft");
const stages = [
  { key: "draft", label: "草稿", description: "编辑工作流定义与版本" },
  { key: "versioned", label: "版本", description: "创建可追踪的版本" },
  { key: "published", label: "已发布", description: "确定当前生效版本" },
  { key: "running", label: "运行", description: "创建并观察 Execution" },
  { key: "recovery", label: "恢复", description: "失败后 Retry / Resume" },
];
const activeIndex = computed(() => {
  const map: Record<string, number> = { draft: 0, versioned: 1, published: 2, pending: 3, running: 3, completed: 3, failed: 4, cancelled: 3 };
  return map[status.value] ?? 0;
});
function openTriggers() { void router.push("/workflows/triggers"); }
function openRuntime() { void router.push("/runtime"); }
</script>

<template>
  <section class="lifecycle-panel" aria-label="工作流生命周期工作台">
    <div class="panel-head"><div><span class="eyebrow">P1 生命周期</span><h2>工作流发布与运行闭环</h2><p>将定义、版本、发布、Trigger、Execution 与恢复操作组织成一条连续的企业工作流。</p></div><el-tag effect="plain">当前阶段：{{ stages[activeIndex].label }}</el-tag></div>
    <div class="steps"><div v-for="(stage, index) in stages" :key="stage.key" :class="['step', { active: index === activeIndex, done: index < activeIndex }]" @click="index === 2 ? openTriggers() : index >= 3 ? openRuntime() : undefined"><span>{{ index + 1 }}</span><div><strong>{{ stage.label }}</strong><small>{{ stage.description }}</small></div></div></div>
    <div class="actions"><span>推荐路径：版本 → 发布 → Trigger → Execution → Trace → Audit</span><div><el-button size="small" @click="openTriggers">管理触发器</el-button><el-button size="small" type="primary" plain @click="openRuntime">查看运行中心</el-button></div></div>
  </section>
</template>

<style scoped>
.lifecycle-panel{position:fixed;right:24px;bottom:20px;z-index:1000;width:min(720px,calc(100vw - 48px));padding:20px 22px;border:1px solid #d0d5dd;border-radius:12px;background:rgba(255,255,255,.98);box-shadow:0 12px 32px rgba(16,24,40,.16)}.panel-head{display:flex;justify-content:space-between;gap:20px}.eyebrow{font-size:10px;color:#667085;font-weight:700;letter-spacing:.08em}.panel-head h2{margin:4px 0;font-size:17px;color:#1d2939}.panel-head p{margin:0;color:#667085;font-size:12px}.steps{display:grid;grid-template-columns:repeat(5,1fr);gap:8px;margin-top:18px}.step{display:flex;gap:8px;min-height:58px;padding:10px;border:1px solid #eaecf0;border-radius:9px;background:#fcfcfd}.step span{display:grid;place-items:center;width:22px;height:22px;flex:0 0 22px;border-radius:50%;background:#f2f4f7;color:#667085;font-size:10px;font-weight:700}.step strong,.step small{display:block}.step strong{font-size:11px;color:#344054}.step small{margin-top:3px;color:#667085;font-size:9px;line-height:1.4}.step.active{border-color:#b8c7e6;background:#eff6ff}.step.active span,.step.done span{background:#2563eb;color:#fff}.step.done,.step:nth-child(n+4){cursor:pointer}.actions{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-top:14px;padding-top:12px;border-top:1px solid #f2f4f7;color:#667085;font-size:10px}.actions div{display:flex;gap:6px}@media(max-width:900px){.lifecycle-panel{right:12px;bottom:12px;width:calc(100vw - 24px)}.steps{grid-template-columns:1fr}.panel-head{flex-direction:column}.actions{align-items:flex-start;flex-direction:column}}
</style>
