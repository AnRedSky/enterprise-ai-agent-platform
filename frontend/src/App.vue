<template>
  <router-view v-if="$route.meta.public" />
  <AppShell v-else />
  <WorkflowLifecycleExperience v-if="$route.path === '/workflows'" />
</template>

<script setup lang="ts">
import AppShell from "./components/AppShell.vue";
import WorkflowLifecycleExperience from "./components/WorkflowLifecycleExperience.vue";
</script>
