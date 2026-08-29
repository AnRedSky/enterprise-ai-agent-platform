<template>
  <router-view v-if="$route.meta.public" />
  <AppShell v-else />
</template>

<script setup lang="ts">
import AppShell from "./components/AppShell.vue";
</script>
