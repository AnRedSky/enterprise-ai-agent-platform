<script setup lang="ts">
withDefaults(defineProps<{
  title: string;
  description?: string;
  eyebrow?: string;
}>(), { description: undefined, eyebrow: undefined });
</script>

<template>
  <header class="ui-page-header">
    <div class="ui-page-header__copy">
      <p v-if="eyebrow" class="ui-page-header__eyebrow">{{ eyebrow }}</p>
      <h1>{{ title }}</h1>
      <p v-if="description" class="ui-page-header__description">{{ description }}</p>
    </div>
    <div v-if="$slots.actions" class="ui-page-header__actions"><slot name="actions" /></div>
  </header>
</template>

<style scoped>
.ui-page-header { display:flex; align-items:flex-end; justify-content:space-between; gap:24px; margin-bottom:24px; }
.ui-page-header__copy { min-width:0; }
.ui-page-header__eyebrow { margin:0 0 4px; color:var(--ui-text-tertiary); font-size:11px; line-height:16px; font-weight:600; letter-spacing:.06em; text-transform:uppercase; }
.ui-page-header h1 { margin:0; color:var(--ui-text-primary); font-size:24px; line-height:32px; font-weight:650; letter-spacing:-.02em; }
.ui-page-header__description { max-width:760px; margin:5px 0 0; color:var(--ui-text-tertiary); font-size:13px; line-height:20px; }
.ui-page-header__actions { display:flex; align-items:center; gap:8px; flex:0 0 auto; }
@media (max-width:700px) { .ui-page-header { align-items:stretch; flex-direction:column; gap:14px; } .ui-page-header__actions { width:100%; } .ui-page-header__actions :deep(.el-button) { flex:1; } }
</style>
