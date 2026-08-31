<script setup lang="ts">
withDefaults(defineProps<{ title?: string; description?: string; bordered?: boolean }>(), { title: undefined, description: undefined, bordered: true });
</script>

<template>
  <section class="ui-surface-card" :class="{ 'is-borderless': !bordered }">
    <header v-if="title || description || $slots.header" class="ui-surface-card__header">
      <div v-if="title || description" class="ui-surface-card__copy"><h2 v-if="title">{{ title }}</h2><p v-if="description">{{ description }}</p></div>
      <div v-if="$slots.header" class="ui-surface-card__actions"><slot name="header" /></div>
    </header>
    <div class="ui-surface-card__body"><slot /></div>
  </section>
</template>

<style scoped>
.ui-surface-card { overflow:hidden; border:1px solid var(--ui-border-default); border-radius:var(--ui-radius-lg); background:var(--ui-bg-surface); box-shadow:var(--ui-shadow-xs); }
.ui-surface-card.is-borderless { border-color:transparent; box-shadow:none; }
.ui-surface-card__header { display:flex; align-items:center; justify-content:space-between; gap:16px; padding:16px 20px; border-bottom:1px solid var(--ui-border-default); }
.ui-surface-card__copy { min-width:0; }
.ui-surface-card__copy h2 { margin:0; color:var(--ui-text-primary); font-size:14px; line-height:20px; font-weight:600; }
.ui-surface-card__copy p { margin:2px 0 0; color:var(--ui-text-tertiary); font-size:12px; line-height:18px; }
.ui-surface-card__actions { display:flex; align-items:center; gap:8px; flex:0 0 auto; }
.ui-surface-card__body { min-width:0; }
</style>
