<template>
  <el-dialog
    :model-value="modelValue"
    :title="title"
    :width="width"
    :close-on-click-modal="false"
    :close-on-press-escape="!loading"
    :show-close="!loading"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <div class="confirm-dialog__content">
      <p class="confirm-dialog__description">{{ description }}</p>
      <slot />
    </div>
    <template #footer>
      <el-button :disabled="loading" @click="$emit('cancel')">{{ cancelText }}</el-button>
      <el-button :type="danger ? 'danger' : 'primary'" :loading="loading" @click="$emit('confirm')">
        {{ confirmText }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    modelValue: boolean;
    title: string;
    description: string;
    confirmText?: string;
    cancelText?: string;
    danger?: boolean;
    loading?: boolean;
    width?: string;
  }>(),
  {
    confirmText: "确认",
    cancelText: "取消",
    danger: false,
    loading: false,
    width: "520px",
  },
);

defineEmits<{
  "update:modelValue": [value: boolean];
  confirm: [];
  cancel: [];
}>();
</script>

<style scoped>
.confirm-dialog__content { display: flex; flex-direction: column; gap: var(--ui-space-3); }
.confirm-dialog__description { margin: 0; color: var(--ui-text-secondary); line-height: 1.6; }
</style>
