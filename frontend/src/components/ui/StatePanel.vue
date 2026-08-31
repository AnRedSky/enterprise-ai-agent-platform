<template>
  <div class="state-panel" :class="`state-panel--${state}`" role="status" :aria-live="state === 'loading' ? 'polite' : 'assertive'">
    <el-icon v-if="state === 'loading'" class="state-icon is-loading"><Loading /></el-icon>
    <el-icon v-else-if="state === 'error'" class="state-icon"><CircleCloseFilled /></el-icon>
    <el-icon v-else-if="state === 'permission'" class="state-icon"><Lock /></el-icon>
    <el-icon v-else-if="state === 'success'" class="state-icon"><CircleCheckFilled /></el-icon>
    <el-icon v-else class="state-icon"><FolderOpened /></el-icon>
    <strong>{{ title }}</strong>
    <span v-if="description">{{ description }}</span>
    <el-button v-if="actionLabel" :type="actionType" @click="$emit('action')">{{ actionLabel }}</el-button>
  </div>
</template>

<script setup lang="ts">
import { CircleCheckFilled, CircleCloseFilled, FolderOpened, Loading, Lock } from "@element-plus/icons-vue";

type State = "loading" | "empty" | "error" | "permission" | "success";
withDefaults(defineProps<{ state: State; title: string; description?: string; actionLabel?: string; actionType?: "primary" | "default" | "danger" | "warning" | "success" | "info" }>(), { actionType: "primary" });
defineEmits<{ action: [] }>();
</script>

<style scoped>
.state-panel { min-height: 180px; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px; padding:24px; text-align:center; border:1px dashed var(--ui-border-default); border-radius:var(--ui-radius-md); background:var(--ui-bg-subtle); }
.state-panel strong { color:var(--ui-text-secondary); font-size:14px; }
.state-panel span { max-width:520px; color:var(--ui-text-tertiary); font-size:12px; line-height:1.6; }
.state-icon { font-size:26px; color:var(--ui-text-tertiary); margin-bottom:2px; }
.state-panel--loading .state-icon { color:var(--ui-color-primary-500); }
.state-panel--error .state-icon { color:var(--ui-color-danger-500); }
.state-panel--permission .state-icon { color:var(--ui-color-warning-500); }
.state-panel--success .state-icon { color:var(--ui-color-success-500); }
.is-loading { animation: state-spin 1s linear infinite; }
@keyframes state-spin { to { transform:rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .is-loading { animation:none; } }
</style>
