<template>
  <div class="page">
    <PageHeader
      eyebrow="Runtime Governance"
      title="审计日志"
      description="按状态筛选真实运行操作记录；Execution 关联使用后端返回的 durable execution_id，可直接进入运行诊断。"
    />
    <AuditLogPanel />
  </div>
</template>

<script setup lang="ts">
import PageHeader from "@/components/ui/PageHeader.vue";
import AuditLogPanel from "./components/AuditLogPanel.vue";
</script>

<style scoped>
.page { min-height:100%; padding:var(--ui-space-8); max-width:1600px; margin:0 auto; }
.page :deep(.audit-panel) { padding:0; }
.page :deep(.audit-panel > .panel-heading) { display:none; }
@media(max-width:700px){.page{padding:var(--ui-space-5)}}
</style>
