<template>
  <div class="page">
    <PageHeader
      eyebrow="Runtime Governance"
      title="Runtime 企业运维中心"
      description="统一观察全局运行态势与 Event、Delivery、SLO、Provider、Alert、Metrics、Audit 和死信；所有数据严格限制在当前租户。"
    />
    <OperationsConsole />
    <OperationsRuntimeCorrelation />
  </div>
</template>

<script setup lang="ts">
import PageHeader from "@/components/ui/PageHeader.vue";
import OperationsConsole from "./OperationsConsole.vue";
import OperationsRuntimeCorrelation from "./OperationsRuntimeCorrelation.vue";
</script>

<style scoped>
.page { min-height:100%; padding:var(--ui-space-8); max-width:1600px; margin:0 auto; }
.page :deep(.operations-console) { padding:0; }
.page :deep(.operations-console > .toolbar > div:first-child) { visibility:hidden; width:0; min-width:0; overflow:hidden; }
.page :deep(.operations-console > .toolbar) { margin-bottom:var(--ui-space-4); align-items:center; }
@media(max-width:700px){.page{padding:var(--ui-space-5)}}
</style>
