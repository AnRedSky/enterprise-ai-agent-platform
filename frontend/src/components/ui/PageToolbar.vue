<script setup lang="ts">
withDefaults(defineProps<{ title?: string; description?: string }>(), { title: undefined, description: undefined });
</script>

<template>
  <section class="ui-page-toolbar">
    <div v-if="title || description" class="ui-page-toolbar__copy">
      <h2 v-if="title">{{ title }}</h2>
      <p v-if="description">{{ description }}</p>
    </div>
    <div class="ui-page-toolbar__content"><slot /></div>
  </section>
</template>

<style scoped>
.ui-page-toolbar { display:flex; align-items:center; justify-content:space-between; gap:16px; min-height:40px; margin-bottom:16px; }
.ui-page-toolbar__copy { min-width:0; }
.ui-page-toolbar__copy h2 { margin:0; color:var(--ui-text-primary); font-size:15px; line-height:22px; font-weight:600; }
.ui-page-toolbar__copy p { margin:2px 0 0; color:var(--ui-text-tertiary); font-size:12px; line-height:18px; }
.ui-page-toolbar__content { display:flex; align-items:center; justify-content:flex-end; gap:8px; min-width:0; }
@media (max-width:700px) { .ui-page-toolbar { align-items:stretch; flex-direction:column; } .ui-page-toolbar__content { justify-content:stretch; flex-wrap:wrap; } }
</style>
